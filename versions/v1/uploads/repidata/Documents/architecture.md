# Architecture — Design Specification

**Project:** Enterprise CDC Replication Platform (working name TBD)
**Document type:** Concept and design specification (master architecture)
**Status:** Design locked for v1 core; deferred items noted

---

## 1. Purpose and Positioning

This document defines the system's components, how data and control flow between them, and the deliberate points of departure from the HVR 6 architecture it competes with. The shape is proven — capture from source transaction logs, compress and encrypt, route through a hub, integrate into targets — because that shape maps onto how regulated enterprises actually approve networks, firewalls, and accreditation packages. The differentiation is in the details: a single static Rust binary everywhere, a first-class designed transport format, an API-first control plane, and zero licensing telemetry.

## 2. System Overview

> **Update (2026-07):** the user-facing hierarchy above the hub is now specified in `fleet-hierarchy.md` — a hub server is a **Fleet**, a logical hub on it a **Virtual Fleet**, with a cross-company **Global Fleet console** (gated by `FleetViewer`) and a strictly downward-editing admin model (SuperAdmin / Global / Fleet / Virtual Fleet Admin). This section's transport-level "hub" vocabulary is unchanged.

Data flows: source database transaction logs → capture agent (parse, filter, compress, encrypt) → hub (relay, durable file log, routing) → integrate agent (burst or continuous apply) → target. Control flows separately: hub server ↔ agents over mTLS for job assignment, checkpoints, and health; users ↔ hub over the REST API via web UI, CLI, or scripts.

### 2.1 Topology decision: hub-routed

Change data flows through the hub (HVR model), not peer-to-peer. Rationale: in zoned networks — defense enclaves, segmented manufacturing — source and target zones frequently cannot communicate directly, but both may talk to a broker host in a management zone. Hub routing means one host to accredit and two firewall paths per pipeline instead of an N×M mesh of change requests. Peer-to-peer transfer is preserved as a future routing *policy* (the file log format and ack protocol are identical either way), deferred, not designed out.

## 3. Components

### 3.1 Hub server

One Rust process providing: the public REST API (the only interface — see section 7), the scheduler (job lifecycle for capture, integrate, refresh, compare), and the file relay (receiving change files from capture agents, storing them durably, serving them to integrate agents, and garbage-collecting on full acknowledgment). One hub server hosts multiple logical hubs, each with its own scheduler state, so a single installation can separate programs, enclaves, or business units.

### 3.2 Repository database

Holds metadata only: location and channel definitions, job state, events, users, license entitlement. Change data never enters the repository — it lives exclusively in the file log. This hard boundary keeps the repository small, fast, and restorable from a plain `pg_dump`. Supported engines are deliberately narrow: PostgreSQL for production; embedded SQLite for dev, lab, and PoC installs so a demo requires zero extra infrastructure. HVR's wide repository-DB support matrix is a testing tax that buys little; we decline it.

### 3.3 Native file log transport

The heart of the system, specified fully in its own document when transport implementation begins; the architectural commitments are:

Framed records: length-prefixed protobuf frames, one per row change, carrying operation type, table identity, before/after images, source position (SCN/LSN/LRSN), and a **change-origin lineage**: an ordered list of (location, channel) entries recording every hop the change has traversed — hop-0, the original producer, first; each capture that reads replicated-in changes appends its own entry. The encoding keeps the per-record cost at a few bytes regardless of chain depth: the file envelope header carries an **origin dictionary** (the distinct (location, channel) pairs appearing in the file), and each record's lineage is a sequence of varint indexes into it. Chain depth is bounded (16 hops); a record arriving at the bound fails capture with a loop-suspected error — never silent truncation of history. The lineage ships in v1 because its consumers pull in different directions and all of them hang off the format: loopback detection (bidirectional) needs the most recent hop, cascading origin filters and audit tracing need the full ordered path, and n-way replication needs both — and retrofitting a shipped file format is a migration. The TimeKey `_origin` column (channel spec 3.1) exposes this same lineage to customers, hop-0 first.

File envelope: each file carries a header with the source position range, a schema epoch, and a checksum; payloads are zstd-compressed then AES-256-GCM encrypted. Files remain encrypted at rest on the hub, not merely in transit.

Ordering and delivery: files are named by pipeline plus monotonic sequence; records within a file are commit-ordered; total order per pipeline follows from the filesystem alone. Files are deleted only after every consuming integrate agent has acknowledged past them, which is what makes broadcast (one-to-many) fan-out safe by construction.

Exactly-once: each integrate agent records its applied position in a small state table inside the target database, updated in the same transaction as the data. Crash replay is idempotent — re-read from the recorded position, skip what's applied.

**Delivery semantics on non-transactional targets.** The co-transactional state table presumes a target with transactions; file stores and Kafka — TimeKey's flagship targets — have none, so each gets a designed equivalent rather than a silent downgrade:

*File targets (S3/ADLS/local).* Output objects are named deterministically from (channel, table identity, integrate sequence), so a replayed sequence rewrites byte-identical objects. Each apply cycle finalizes with an atomic **manifest** update — a small state object recording the highest applied sequence, written last via the store's atomic put/rename primitive — serving as the state table's equivalent. Recovery lists objects at and beyond the manifest position and reconciles: objects at manifested sequences are final; orphans beyond it are overwritten by the replay. Net effect is effectively-once — zero missing and zero duplicate records in the final object set — proven by ARC-11.

*Kafka targets.* Integrate uses the transactional producer: each apply cycle publishes its change records and its position marker (to a compacted per-channel state topic) inside one Kafka transaction; on restart the agent reads its position from the state topic and resumes past it. Consumers at `read_committed` observe exactly-once delivery; the `read_uncommitted` caveat (aborted duplicates visible) is stated in the connector documentation, not discovered. Proven by ARC-12 when the Kafka connector lands.

Where a specific store cannot supply the required primitive (no atomic rename, no transactions), the class capability matrix states the downgraded guarantee — at-least-once with documented dedup keys — explicitly, never silently.

### 3.4 Agents

A single universal binary containing every source reader and target writer; the hub assigns the role per job. Specified in `agent.md`.

### 3.5 Kafka's place

Kafka is a target connector on the roadmap, not core infrastructure. Requiring a Kafka cluster would put the product in Debezium's shadow while destroying its air-gap story; the native file log provides the durable ordered transport without external middleware. The pitch line stands: Debezium-compatible when you want Kafka, HVR-simple when you don't.

## 4. The Life of a Single Change — nothing hidden

The transparency principle applied to the platform's core: what actually happens, step by step, when an application commits `UPDATE orders SET status='SHIPPED' WHERE id=42` on an Oracle source replicating to Snowflake. Every step below is observable — in the event log, the metrics, or the published file format — because an operator who can follow this chain can diagnose anything the platform ever does.

1. **The database writes redo.** Oracle records the change in its redo log with the row images supplemental logging guarantees (at least the key columns), stamped with an SCN.
2. **The capture agent reads it at the log layer** — directly from the redo file (or via BFILE/ASM per the location's access method), never through LogMiner, never through a SQL session touching the table.
3. **The parser filters first, decodes second.** The redo record's object ID is checked against the channel's enrollment snapshot; changes to unsubscribed tables are skipped before column decoding — they cost almost nothing and never leave the host.
4. **The change becomes a frame**: one protobuf record carrying operation type, table identity, before/after images, the SCN, transaction ID, commit timestamp, and the change-origin lineage — a single entry here (this channel, this location), because this is hop-0; in a cascade, each subsequent capture appends its own entry to the chain.
5. **Frames accumulate into a change file** in commit order, sealed with a header (SCN range, schema epoch, checksum), compressed with zstd, encrypted with AES-256-GCM — on the agent, before any network.
6. **The file ships to the hub over mTLS** and is written durably to the hub file store under `<channel>/<sequence>`. Only now does the capture agent advance its checkpoint past this SCN — a crash before this point means re-reading redo, never losing data.
7. **The hub relays, it does not interpret.** The file sits encrypted in the file log; the repository records only its existence and sequence. Row data never enters the repository — the hub could be subpoenaed, imaged, or lost and the payloads remain ciphertext.
8. **The integrate agent pulls the file**, verifies the checksum, decrypts, and stages the changes for its apply mode — for Snowflake, a burst cycle: changes land in a staging table via the bulk path.
9. **The merge applies the burst** — insert/update/delete against the target table per the channel's replication style — **and in the same transaction updates the state table** with this file's position and integrate sequence. That co-transactionality is the exactly-once guarantee in one sentence: the data and the record of having applied it commit together or not at all.
10. **The integrate agent acknowledges the sequence to the hub.** When every consuming integrate (broadcast fan-out included) has acked past a file, the hub garbage-collects it.
11. **A crash anywhere replays safely.** Capture re-reads redo from its checkpoint; integrate re-pulls files past the position in the target's state table and skips what's already applied. The operator sees the recovery in the event log; the compare feature can prove the result.
12. **The fleet dashboard's latency number** is the timestamp delta between step 1's commit and step 9's apply — measured, not estimated.

The same chain serves refresh (files carry snapshot rows instead of changes, step 9's merge becomes stage-and-swap) and compare (files carry checksums). One transport, one discipline, everywhere.

## 5. Security Architecture

All hub↔agent and client↔hub connections use TLS; agent connections use mutual TLS with certificate pinning in both directions (agent keypair generated at first start and pinned in the repository; hub client certificate optionally allowlisted on the agent). Payload encryption (AES-256-GCM) is independent of transport encryption. No component ever phones home: license validation is offline against signed license files, and there is no usage telemetry anywhere in the product. Credentials for source/target databases are stored encrypted in the repository with envelope encryption; plaintext credentials never appear in logs, API responses, or exported configurations.

## 6. Licensing Architecture

Enterprise flat license: unlimited sources, channels, rows, and hubs for one legal entity plus subsidiaries; zero metering, hence zero enforcement machinery beyond validating a signed license file at hub start and surfacing entitlement status in the Admin UI. Commercial model: perpetual license plus annual maintenance (updates, new connectors, support); if maintenance lapses, the software continues running forever at the last entitled version — replication never stops over a billing state. Grace behavior on expiry of a term-limited evaluation license: alerts and no new pipeline creation; running pipelines are never halted. Dependency policy: MIT and Apache-2.0 crates only, enforced by cargo-deny in CI; the Oracle Instant Client is redistributed per its license terms and the decision is documented.

## 7. Interfaces

The web UI is a pure client of the public REST API — no private endpoints, no backdoors; anything the UI does, a curl command can do. The API ships an OpenAPI specification from which the reference documentation is generated, so docs cannot drift from behavior. The CLI is a standalone static binary speaking only the REST API: drop it on any machine, point it at the hub with a token — no product installation required, unlike HVR's remote CLI. Channel and location definitions are exportable/appliable as version-controlled configuration through the CLI, enabling GitOps workflows.

## 8. Component Mapping vs HVR 6

| HVR 6 | This platform | Delta |
|---|---|---|
| Hub Server (REST + Scheduler) | Hub server (REST + scheduler + relay) | Relay is an explicit, designed component |
| Repository database (wide DB matrix) | PostgreSQL prod / SQLite dev | Narrowed deliberately |
| Router files | Native file log | Elevated to a specified, published format |
| Logical hubs | Logical hubs | Kept |
| Jobs (capture/integrate/refresh/compare) | Same job model | Kept |
| HVR Agent | Universal agent binary | One artifact, static, all connectors |
| Agentless mode | Kept | Postgres wire protocol, Oracle SQL*Net/BFILE |
| Web UI | Web UI | Pure REST client; fleet view native |
| CLI (requires install for remote) | Standalone static CLI | No install footprint |
| REST API | REST API | OpenAPI-generated docs, UI parity guaranteed |

## 9. Deferred Items (documented, not designed out)

Hub high availability (active/passive failover) is a to-do for v2. The design quietly enables it: the repository is plain PostgreSQL and all transport state lives in the file log, so a standby hub pointing at the same repository and file store is the natural path — no exotic clustering. Peer-to-peer routing is a future config option per section 2.1. AIX/Solaris agents are deferred; agentless mode covers classic Unix sources meanwhile.

### 9.1 V1 readiness gates: storage safety and upgrade safety

File-log capacity and repository upgrades are release blockers for v1, not deferred operational polish. Neither may rely on an operator discovering a limit after data movement has stopped.

| Risk | Required v1 behavior | Required release evidence |
|---|---|---|
| Hub file-store exhaustion and a slow consumer | Each logical hub has an explicit file-store quota and reserved headroom. The hub continuously exposes unacknowledged bytes, oldest unacknowledged age, capture ingress rate, integrate egress rate, and forecast time to quota. Configurable warning and throttle thresholds must be set from benchmarked sizing guidance before release. Files remain protected by the joint acknowledgement low-water mark: pressure never permits deleting an unacknowledged file. Before the hard limit, the hub refuses new file admission and capture either uses its configured spool within budget or pauses at its last durable checkpoint with an alert; it never drops a source position or emits a partial file. | ARC-13 passes under a held-consumer disk-pressure drill. Published sizing guidance covers volume tiers, outage/spool assumptions, source-log retention, and the default thresholds. |
| Repository schema migration during an upgrade | Every migration is ordered, versioned, and checksummed in a repository migration ledger. Upgrade preflight verifies the starting version, migration checksum history, free capacity, and a recoverable repository backup. The hub acquires an upgrade lock, stops new scheduler dispatch, and waits for active work to reach a checkpoint before applying migrations. PostgreSQL migrations run transactionally; destructive changes require a staged, backward-compatible release rather than an in-place irreversible rewrite. A failed migration prevents job dispatch and leaves the prior schema usable. Schema downgrade is never automatic: rollback is either the prior binary when compatibility is declared or restoration of the verified pre-upgrade backup. | ARC-14 passes for a normal upgrade, an injected migration failure, and a restore-to-prior-version drill with compare-clean pipelines. The release runbook includes preflight, checkpoint/drain, rollback, and recovery timing. |

Exact quota defaults and migration compatibility windows are benchmark-derived release deliverables. They may not remain unspecified at v1 code freeze.

## 10. Test Plan

Four phases with entry/exit conditions; the standing rule applies (procedure executed, results observed, evidence archived — no procedure, no pass), and the full ARC suite reruns on every merge touching transport, hub, or licensing code.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Transport invariants | ARC-04, ARC-08 | Unit (property-based) | File format implemented | All pass in CI; tamper cases fail closed |
| B | End-to-end pipeline | ARC-01, ARC-05, ARC-07 | Integration lab, TPC-C | Phase A exit; hub + agents runnable | Compare-clean pipeline; parity sweep and repo audit green |
| C | Failure and recovery | ARC-02, ARC-03, ARC-06, ARC-11, ARC-13 | Chaos harness + lab file target | Phase B exit | Kill/partition/restore drills all pass, incl. file-target replay convergence and storage-pressure safety |
| C2 | Non-transactional delivery (gated) | ARC-12 | Lab Kafka cluster | Kafka connector implemented | Exactly-once proven at read_committed under repeated kills |
| D | Governance and upgrade gates | ARC-09, ARC-10, ARC-14 | Release CI and upgrade lab | License and migration machinery implemented | Governance gates green; upgrade and rollback drills pass on the release artifact |

### 10.1 Methods

Architecture-level verification runs at four levels, all gated in CI on every merge.

**Unit: transport invariants.** The file log is tested exhaustively in isolation — frame encode/decode round-trips across every column type, envelope checksum and AES-GCM authentication (tampered files must fail closed), sequence ordering, and origin-lineage propagation (single-hop and appended-chain cases) — with property-based tests (proptest) generating adversarial inputs.

**Integration: the lab pipeline.** The Docker lab (PostgreSQL 17 seeded from the existing pg17-lab setup, later Oracle Free 23ai, SQL Server, DB2) runs HammerDB TPC-C to generate realistic change volume through complete pipelines. Every integration run ends with a compare job proving source equals target — the product verifies its own correctness, and that verification gates the merge.

**Chaos: crash and partition.** A harness kills the hub, kills agents, and severs networks (network-namespace partitions) at randomized points under load, then asserts checkpoint-correct resume with zero loss and zero duplicates (ARC-02, ARC-03). GC discipline is verified by holding one consumer's acks and asserting file retention.

**Sweeps: promises kept.** Automated audits enforce the architectural promises: the UI-vs-API parity sweep replays every UI operation as documented REST calls (ARC-07); a repository schema audit asserts no row-change data (ARC-05); log and export scans assert no plaintext credentials; restore drills rebuild a hub from pg_dump plus the file log (ARC-06); cargo-deny and the static-linkage check run on every build (ARC-10).

## 11. Test Procedures

### ARC-01 — End-to-end pipeline correctness
**Steps:** (1) Stand up the lab pipeline (Postgres → hub → Postgres). (2) Run HammerDB TPC-C for 30 minutes. (3) Drain; run compare across all channel tables.
**Expected:** Compare reports zero differences; latency and throughput recorded as baseline numbers.
**Evidence:** Compare report, metrics snapshot.

### ARC-02 — Hub kill and checkpoint-correct resume
**Steps:** (1) Under TPC-C load, kill the hub process at a randomized point (repeat run 5×, varied points). (2) Restart the hub. (3) Observe capture and integrate resume from checkpoints; drain; compare; duplicate-check target keys.
**Expected:** All 5 runs: automatic resume, compare clean, zero duplicate keys; recovery visible in the event log.
**Evidence:** 5 compare reports, duplicate-check results, event-log excerpts.

### ARC-03 — Ack-based GC with a held consumer
**Preconditions:** Broadcast channel to targets T1, T2; ability to pause T2's integrate.
**Steps:** (1) Pause T2; run load 15 minutes. (2) Sample the hub file inventory: files past T1's ack must be retained pending T2. (3) Resume T2; drain. (4) Verify GC advances to the joint low-water mark; compare both targets.
**Expected:** No file GC'd before both acks; post-drain GC advances; both compares clean.
**Evidence:** Inventory samples, GC log, compare reports.

### ARC-04 — Encryption fails closed
**Steps:** (1) Capture a change file from the hub store; attempt to read it without the payload key with the file-inspection tool (header must read, payload must not). (2) Flip one payload byte; feed to an integrate agent. (3) Audit configuration surface for any mode that would disable payload encryption while keeping TLS.
**Expected:** Payload unreadable without the key; tampered file rejected on AES-GCM authentication with a logged integrity error and no partial apply; no TLS-only configuration exists.
**Evidence:** Tool output, rejection log, configuration audit.

### ARC-05 — Repository contains no row data
**Steps:** (1) After a full TPC-C benchmark run, dump the repository schema and row samples. (2) Run the automated audit asserting no table stores change payloads; grep dumps for seeded canary values that flowed through the pipeline.
**Expected:** Audit passes; zero canary hits in the repository.
**Evidence:** Audit output, grep results.

### ARC-06 — Hub restore from backup plus file log
**Steps:** (1) Under load, take a pg_dump of the repository. (2) Destroy the hub host (retain the file store volume). (3) Provision a fresh hub; restore the dump; attach the file store. (4) Verify all pipelines resume; drain; compare.
**Expected:** Full resume with zero loss/duplication; total recovery time recorded.
**Evidence:** Restore transcript, compare reports, timing.

### ARC-07 — UI-vs-API parity sweep
**Steps:** (1) Enumerate every UI operation from the Playwright suite. (2) For each, execute the equivalent documented REST call against a twin hub. (3) Diff resulting states.
**Expected:** Every UI operation reproducible via documented API; state diffs empty; any UI-only capability fails the sweep.
**Evidence:** Sweep report with per-operation results.

### ARC-08 — Origin lineage across a cascade
**Steps:** (1) Run a two-hop cascade under load. (2) Decode 1,000-record samples from hop-1 and hop-2 files, including the origin dictionaries from the file headers. (3) Assert lineage per the format spec at each hop: hop-1 records carry exactly one entry (the S→M pipeline and source location); hop-2 records carry exactly two entries in order (the original entry first, the M→T entry appended). (4) Verify dictionary-index encoding decodes to the correct pairs and per-record lineage cost stays within the documented byte budget.
**Expected:** 100% of sampled records carry a correct, complete, correctly ordered lineage chain; hop-2's first entry equals hop-1's only entry (hop-0 traceability); encoding budget held.
**Evidence:** Decoded samples with assertion results, per-record size distribution.

### ARC-09 — License behavior on lapse
**Steps:** (1) Start a hub with a maintenance-expired (but perpetual) license under running pipelines; observe for 24 hours. (2) Attempt to create a new pipeline (per documented lapse behavior). (3) Attempt to upgrade the hub to a version post-dating entitlement.
**Expected:** Replication never interrupts; lapse-mode behaviors match documentation exactly; version upgrade refused with a clear, documented message; zero network calls attempted by license validation (egress capture).
**Evidence:** 24-hour pipeline continuity metrics, refusal messages, empty egress capture.

### ARC-10 — Dependency and linkage gates
**Steps:** (1) On a branch, add a GPL-licensed crate; push; observe CI. (2) On the release artifact, run the linkage audit.
**Expected:** cargo-deny fails the GPL branch; linkage audit passes on release (static, Oracle-client exception documented).
**Evidence:** CI results, audit output.

### ARC-11 — File-target replay idempotence
**Preconditions:** TimeKey channel into the lab file target (S3-compatible store); chaos harness; a never-killed control run of the identical source change stream for reference.
**Steps:** (1) Under TPC-C load, kill the integrate agent at randomized points mid-cycle, repeated 5×, including at least one kill in the window between object writes and the manifest update. (2) Restart each time; let replay complete and the run drain. (3) List the final object set; verify against the manifest and the published deterministic naming scheme — no orphans, no sequence gaps. (4) Read every object back through the published-format reader; assert record-level equivalence to the control run, byte-identical objects at overlapping sequences, and zero duplicates by (commit position, transaction sequence, table, key).
**Expected:** All 5 runs converge to an object set identical to the control's; zero missing and zero duplicate records; the kill between data and manifest is healed by overwrite-on-replay; final manifest position matches the object set.
**Evidence:** Object listings, manifest states, read-back duplicate-check results, control-run diff (empty).

### ARC-12 — Kafka exactly-once *(gated: enters the active matrix when the Kafka connector lands)*
**Steps:** (1) TimeKey channel into a lab Kafka cluster with the transactional integrate path; one consumer at `read_committed`, one at `read_uncommitted`. (2) Kill the integrate agent mid-transaction, repeated 5×; restart and drain each time. (3) Reconcile the `read_committed` consumer's record set against the source change stream; duplicate-check by (commit position, transaction sequence, table, key); verify position resume came from the state topic.
**Expected:** The `read_committed` consumer observes every source change exactly once across all kill points; resume positions trace to the state topic; `read_uncommitted` behavior matches the documented caveat.
**Evidence:** Consumer record accounting, duplicate-check results, state-topic position log.

### ARC-13 — File-store pressure and safe capture back-pressure
**Preconditions:** Broadcast pipeline with a configurable per-hub file-store quota, capture spool enabled and sized for the test, capacity metrics and alerts enabled, and a continuous TPC-C workload.
**Steps:** (1) Hold one integrate consumer so its acknowledgement stops, then run capture until the warning and throttle thresholds are crossed. (2) Verify the capacity forecast, unacknowledged-byte and age metrics, and alerts against the observed file-store state. (3) Continue until the hub refuses further file admission; verify that capture spools in order without exceeding its budget, then repeat with spool disabled and verify capture pauses at its durable checkpoint. (4) Restore the consumer and hub capacity; drain all backlog and run compare against every target.
**Expected:** No unacknowledged file is deleted; warnings and throttle occur before the hard limit; neither configuration loses a source position, creates a partial file, or exceeds its configured disk budget; the recovered targets compare clean. The documented sizing forecast agrees with measured exhaustion time within the stated tolerance.
**Evidence:** Capacity metrics and alert timeline, hub file inventory and acknowledgement samples, agent spool/stop logs, configured budgets, and post-recovery compare reports.

### ARC-14 — Repository migration, failed-upgrade, and rollback safety
**Preconditions:** A supported prior hub release with populated repository metadata, active lab pipelines, a verified repository backup, and a target release containing at least one representative schema migration.
**Steps:** (1) Run upgrade preflight; archive its version, checksum, backup, capacity, and compatibility report. (2) Upgrade while pipelines are active; verify new dispatch stops, active work checkpoints, migrations apply under the upgrade lock, and pipelines resume. (3) Run a second upgrade with an injected migration failure; verify no job dispatch begins and the prior schema and binary remain usable. (4) Execute the documented rollback path from the verified backup to the prior release, resume pipelines, drain, and compare.
**Expected:** A successful upgrade preserves definitions, job history, and checkpoint-correct replication; an injected failure leaves no partial schema or scheduled work; rollback restores the declared prior-version state with zero source-to-target divergence. Recovery timing is recorded against the release objective.
**Evidence:** Preflight and migration-ledger reports, backup checksum and restore transcript, scheduler and event-log excerpts, schema diffs, and compare reports for the upgrade, failure, and rollback runs.

## 12. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| ARC-01 | End-to-end pipeline (Postgres → file log → Postgres) delivers a TPC-C change stream with source-equals-target proven by compare |
| ARC-02 | Kill the hub mid-stream: capture and integrate resume from checkpoints on restart with zero loss and zero duplicates |
| ARC-03 | Broadcast to two targets: file GC occurs only after both integrates acknowledge; deleting one target's ack state halts GC |
| ARC-04 | Change files on hub disk are unreadable without the payload key (AES-GCM verified); TLS-only capture without payload encryption is not possible in any configuration |
| ARC-05 | Repository contains zero row-change data after a full benchmark run (schema audit) |
| ARC-06 | Hub restore from pg_dump plus existing file log resumes all pipelines correctly |
| ARC-07 | Every UI operation is reproducible via documented REST calls (automated UI-vs-API parity sweep) |
| ARC-08 | Origin lineage present, complete, and correctly ordered on every record across a cascading two-hop pipeline: hop-2 records carry the two-entry chain whose first entry traces to hop-0 |
| ARC-09 | Hub start with an expired maintenance term: replication continues; upgrade to a post-entitlement version is refused with a clear message |
| ARC-10 | cargo-deny gate fails the build on introduction of a GPL-family dependency |
| ARC-11 | File-target integrate killed mid-cycle (including between data writes and the manifest update) converges on replay to an object set with zero missing and zero duplicate records, identical to an uninterrupted control run |
| ARC-12 | *(gated on the Kafka connector)* Kafka integrate under repeated mid-transaction kills delivers every source change exactly once to read_committed consumers, resuming position from the state topic |
| ARC-13 | Held-consumer disk pressure crosses warning, throttle, and admission-refusal thresholds without deleting unacknowledged files, losing source positions, emitting partial files, or exceeding configured spool/storage budgets; recovery drains and compares clean |
| ARC-14 | A normal repository migration, an injected migration failure, and rollback to a verified pre-upgrade backup preserve the declared schema state, prevent unsafe job dispatch, and converge active pipelines with zero source-to-target divergence |

## 13. Open Questions

The file-store and repository-upgrade policies are v1 readiness gates in section 9.1, with ARC-13 and ARC-14 as their required proof. Exact sizing defaults and compatibility windows remain to be benchmarked before release; they are no longer open design questions. Naming: product and binary names TBD.
