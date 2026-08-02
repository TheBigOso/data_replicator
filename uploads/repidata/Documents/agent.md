# Agent — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design locked; AIX/Solaris deferred

---

## 1. Purpose and Positioning

The agent is the platform's workhorse: a single universal binary installed near source and target data stores that performs capture, integrate, refresh, and compare work under the hub's direction. One artifact, one install, every connector — the hub assigns the role per job. There is no "source agent package" versus "target agent package," no feature editions, and (per the flat license) nothing to entitle per-agent. The agent is a static Rust binary with no runtime dependencies, which matters disproportionately on locked-down, change-controlled hosts.

## 2. Why Agents (and When Not)

Agents exist for the same reasons HVR's do, all preserved: reading transaction logs at native speed requires local access no database session can match in high-volume environments; filtering at the source means unsubscribed tables never leave the host (in our design, never even get decoded — filtering happens inside the redo/WAL parser); compression before the wire (zstd, commonly ~10x) multiplies effective WAN bandwidth; and distributing parse/apply work off the hub is what makes the setup scale. Agentless mode is fully supported where footprint matters more than throughput: PostgreSQL over the wire protocol, Oracle over SQL*Net with BFILE redo access (the RDS answer). The trade-off is documented per location class.

## 3. Deployment Model

One binary (`replagent`, name TBD) containing all source readers and target writers. Runs as a systemd service on Linux and a Windows service on Windows. The hub server embeds the same agent code — "onebox" mode gives PoCs and small shops a complete installation on a single host. Platforms at launch: Linux (x86_64, aarch64) and Windows. AIX and Solaris are deferred (Rust toolchain maturity); classic Unix sources are served agentlessly until demand justifies the port. The Kafka/librdkafka lesson generalizes: anything that would compromise the fully-static build lives behind a Cargo feature flag.

## 4. Enrollment and Identity

HVR's setup mode — a 60-minute post-install configuration window, or a token-protected variant — is replaced by **enrollment tokens**, the pattern operators already trust from Kubernetes: an admin generates a one-time token on the hub (UI or CLI), runs `replagent enroll --hub https://hub:PORT --token ...` on the new host, and the mutual certificate exchange and pinning happen automatically. No timing window to miss, no unconfigured-agent limbo. On first start the agent generates its keypair; enrollment pins the agent certificate in the repository and delivers the hub's client certificate for the agent's allowlist.

## 5. Connectivity and Security

All hub↔agent traffic is mutual TLS with certificate pinning in both directions. Two connection directions are supported per agent: hub-initiated (hub dials the agent's listener port — HVR parity) and **agent-initiated** (the agent dials out to the hub and holds the tunnel; jobs multiplex over it). Agent-initiated exists because in locked-down enclaves "outbound 443 to the hub" is approvable in a week while "inbound port on the database server" is a change-board fight. Connection modes for authentication mirror HVR: agent-user credentials, cert-pinned anonymous (trusted hubs only), or both; an agent-admin role permits remote configuration.

## 6. Runtime Behavior

Capture agents parse the source log, filter to subscribed tables inside the parser, frame records (with origin markers), compress, encrypt, and ship files to the hub, advancing their checkpoint only after durable hub write. Integrate agents pull files, decrypt, and apply via burst (stage + merge) or continuous mode, recording position in the target-side state table transactionally.

**Optional local spool** (off by default): when enabled with a bounded disk budget, a capture agent that loses the hub continues writing change files to local disk and drains them in order when the hub returns — converting a hub outage from a replication incident racing source log retention into a non-event. Off by default because surprise disk consumption on database hosts is a DBA relationship killer; when on, the budget, current usage, and drain state are visible on the agent's page and the API.

## 7. Upgrades

Hub-orchestrated, admin-approved: the hub stages a new agent binary; an administrator approves per location or fleet-wide; each agent swaps itself atomically and health-checks, rolling back automatically on failure. Staged and approval-gated specifically so change-controlled environments retain control — the orchestration removes the host-by-host chore, not the change board. Mixed-version operation (hub newer than agents) is supported within a documented compatibility window so fleets upgrade on their own schedule.

## 8. HVR Parity Matrix

| HVR Agent feature | This platform | Delta |
|---|---|---|
| One installation, capture or integrate | One universal static binary | No runtime deps, all connectors included |
| Hub can act as agent | Onebox mode | Kept |
| Compression before send | zstd at agent | Kept |
| TLS by default, cert auto-generation, pinning | mTLS + pinning both directions | Payloads additionally encrypted at rest |
| Setup mode (timed / token) | Enrollment tokens | No timing window; k8s-join pattern |
| Connection modes (user / anonymous+pinned / both) | Same three modes | Kept |
| Agent users, AgentAdmin | Agent accounts + admin role | Kept |
| Hub-initiated connection | Supported | Kept |
| — | Agent-initiated connection | New: firewall-friendly outbound tunnel |
| — | Optional bounded local spool | New: hub-outage resilience |
| Manual host-by-host upgrades | Orchestrated approved upgrades | New: atomic swap, auto-rollback |
| Linux, Unix (AIX/Solaris), Windows | Linux + Windows | AIX/Solaris deferred; agentless covers |

## 9. Test Plan

Phased plan; the standing rule applies (procedure executed, results observed, evidence archived — no procedure, no pass), and the full suite reruns as regression on every merge touching this area.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Identity and security | AGT-01, AGT-02, AGT-03, AGT-04 | Network namespaces + wire capture | Enrollment and mTLS implemented | Token lifecycle, pinning, zero-inbound, and filtering proven |
| B | Outage resilience | AGT-05, AGT-06 | Chaos harness (timed partitions) | Phase A exit; spool implemented | Spool-on and spool-off behaviors proven under load |
| C | Fleet and artifacts | AGT-07, AGT-08, AGT-09, AGT-10 | Three-agent fleet; release CI | Orchestrated upgrade implemented | Upgrade/rollback drill clean; quick-start and linkage gates green |

### 9.1 Methods

Agent testing leans on **network namespaces** to make security claims falsifiable: each lab agent runs in its own namespace with explicit firewall rules, so "zero inbound rules" for agent-initiated mode (AGT-02) is asserted against actual packet filters, not documentation. Enrollment tests (AGT-01, AGT-03) exercise the token lifecycle — single use, expiry, replay refusal — and certificate pinning with deliberately wrong hub identities.

**Filtering audits** (AGT-04) verify source-side filtering with three independent assertions, because the wire is compressed and encrypted before transmission and therefore can never show a plaintext canary regardless of whether the filter works — a grep of ciphertext passes vacuously. The assertions that can actually fail: **parser filter counters** (every decoy change skipped before column decode, zero decoy decodes); **pre-encryption frame inspection** via the diagnostic frame tap (a test-build hook, like AGT-07's corruption hook, that mirrors framed records to a local file before compression and encryption — the last point where a leaked decoy row would still be legible); and a **differential wire-volume measurement** — bytes shipped per unit of TPC-C work with the decoy load running versus paused must be equal within a documented tolerance, since correctly filtered decoy changes add nothing to the stream. The raw-capture canary grep is retained as a cheap sanity check, understood to be necessary but nowhere near sufficient.

**Spool tests** (AGT-05, AGT-06) partition the hub for timed outages under load, asserting bounded disk growth against the configured budget, in-order drain, and compare-verified zero loss/duplication — and, with spool disabled, the documented stall-and-alert behavior with zero agent-host disk growth.

**Upgrade orchestration** (AGT-07, AGT-08) runs a three-agent fleet under live load through staged upgrades, including a deliberately corrupted binary on one host to prove isolated auto-rollback, and a full four-job-type pass in the mixed-version window. **Artifact checks** (AGT-09, AGT-10) gate every release: the onebox quick-start executes end-to-end in CI, and the linkage audit runs on the release binary itself.

## 10. Test Procedures

Each procedure below verifies one acceptance criterion. A criterion is checked off only when its procedure has been executed, all expected results observed, and the listed evidence archived in the test run record. Commands use the working binary name `replagent`; substitute the final name.

### AGT-01 — Enrollment token lifecycle

**Preconditions:** Hub running in the lab; a fresh agent host (clean container/VM) with the agent binary present but never enrolled.

**Steps:**
1. On the hub, generate a one-time enrollment token: `replctl agent-token create --location LAB-AG1 --ttl 15m`. Record the token.
2. On the fresh host, run `replagent enroll --hub https://hub.lab:4340 --token <token>`.
3. Verify enrollment: on the hub, `replctl agents list` shows LAB-AG1 with a pinned certificate fingerprint; on the agent, the hub client certificate appears in the allowlist store.
4. Start a trivial stream through this agent and confirm a job runs.
5. On a second fresh host, attempt `replagent enroll` with the **same token**.
6. Generate a new token, wait past its TTL, and attempt enrollment with the expired token.

**Expected results:** Step 2 completes with a single command and no manual certificate handling. Step 4 job succeeds over pinned mTLS. Step 5 is refused with a "token already used" error. Step 6 is refused with a "token expired" error. All three token events (used, replay-refused, expiry-refused) appear in the hub audit log.

**Evidence:** Command transcripts, hub audit log excerpt, certificate fingerprints from both sides matching.

### AGT-02 — Agent-initiated mode with zero inbound rules

**Preconditions:** Agent host in a dedicated network namespace with a default-deny inbound firewall (only established/related allowed); outbound to hub port permitted.

**Steps:**
1. Dump the host firewall ruleset (`nft list ruleset` or `iptables-save`) and archive it — confirm no inbound accept rules exist for any agent port.
2. Configure the agent for agent-initiated connection mode; restart the agent service.
3. Confirm the tunnel: hub UI/API shows the agent connected with direction "agent-initiated."
4. Run one job of each applicable type through this agent (capture cycle against the lab Postgres, integrate into a lab target, refresh, compare).
5. During the run, capture packets on the agent namespace and verify no inbound connection establishment (all TCP sessions initiated from agent side).

**Expected results:** All four job types complete. Packet capture shows exclusively agent-originated sessions. Firewall ruleset unchanged throughout.

**Evidence:** Archived ruleset, packet capture summary, job completion records.

### AGT-03 — Hub certificate allowlist enforcement

**Preconditions:** Enrolled agent with `only-from-hub-certificates` allowlist populated; a second "rogue hub" instance in the lab with its own client certificate.

**Steps:**
1. From the legitimate hub, run a job through the agent — confirm success (baseline).
2. Point the rogue hub at the agent's address and attempt a connection/job assignment.
3. Inspect agent logs for the rejection event.

**Expected results:** Step 2 is rejected at the TLS layer (certificate not in allowlist); no job executes; the agent logs a pinning-violation event with the presented certificate's fingerprint; the legitimate hub remains unaffected.

**Evidence:** Agent log excerpt with rejection event, rogue hub's failed-connection error.

### AGT-04 — Source-side filtering audit

**Preconditions:** Lab Postgres with the TPC-C schema plus two decoy tables (`DECOY_A`, `DECOY_B`) receiving continuous inserts of a known 64-byte canary pattern at a write rate comparable to the TPC-C change volume; a stream subscribing only to the TPC-C tables; packet-capture sidecar on the capture agent's namespace; a test build with the **diagnostic frame tap** enabled (mirrors framed records to a local file before compression and encryption). Note: because wire traffic is zstd-compressed and AES-256-GCM encrypted, absence of the canary in the raw capture proves nothing by itself — the assertions below are ordered by evidentiary weight.

**Steps:**
1. **Baseline window:** run the capture stream under TPC-C alone (decoy writers paused) for 15 minutes; record wire bytes shipped to the hub and the agent's frames-emitted counter, normalized per unit of TPC-C work (transactions completed).
2. **Mixed window:** resume the decoy writers alongside TPC-C at the matched rate for 15 minutes; record the same measurements.
3. Read the parser filter counters for both windows: redo records inspected, records skipped-before-decode per table, records decoded per table. The decoy tables' skip counts must account for the full decoy write volume; their decoded counts must be zero.
4. Search the diagnostic tap output from both windows for the canary pattern and for the decoy tables' object identifiers; both must be entirely absent.
5. Compute the differential: normalized wire volume in the mixed window versus baseline. The decoy load must add no wire volume beyond the documented measurement tolerance (±3%).
6. Sanity check: search the raw (encrypted) packet capture for the canary pattern — expected absent, recorded as corroboration only.
7. Confirm via compare that the subscribed tables replicated correctly across both windows.

**Expected results:** Parser counters show every decoy change skipped before column decode and zero decoy decodes; the pre-encryption tap contains no canary bytes and no decoy table identity in either window; mixed-window normalized wire volume equals baseline within tolerance; raw-capture grep clean; compare clean.

**Evidence:** Per-window counter snapshots, tap search output, wire-volume differential worksheet, raw-capture search output, compare report.

### AGT-05 — Local spool under hub outage (enabled)

**Preconditions:** Capture agent with spool enabled, budget set to 2 GB; TPC-C load running; hub reachable.

**Steps:**
1. Record the current capture checkpoint and target row counts.
2. Partition the hub from the agent (network namespace rule) for 30 minutes while the TPC-C load continues.
3. During the outage, sample the agent's spool metrics every 5 minutes (usage, file count, oldest sequence).
4. Heal the partition; observe drain.
5. After drain completes, run compare source-vs-target over the affected tables.
6. Repeat the outage with a deliberately undersized budget (e.g. 100 MB) to force budget exhaustion; observe behavior.

**Expected results:** Capture never stalls during step 2; spool usage grows but never exceeds 2 GB; files drain strictly in sequence order after healing; compare reports zero differences; step 6 produces the documented budget-exhausted behavior (controlled pause with alert — not silent data loss, not budget overrun).

**Evidence:** Spool metric samples, drain-order log, compare report, budget-exhaustion alert.

### AGT-06 — Default behavior without spool

**Preconditions:** Same as AGT-05 but spool disabled (default); disk-usage monitor on the agent host.

**Steps:**
1. Record agent-host disk usage baseline.
2. Partition the hub for 15 minutes under load.
3. Observe stream state and alerts during the outage; sample agent-host disk usage.
4. Heal and confirm resume; run compare.

**Expected results:** Stream enters the documented stalled state with an alert within one health interval; agent-host disk usage stays flat (no hidden buffering); on heal, capture resumes from checkpoint; compare shows zero loss/duplication (source log retention permitting, per documented behavior).

**Evidence:** Alert record, disk-usage series, compare report.

### AGT-07 — Orchestrated fleet upgrade with rollback

**Preconditions:** Three enrolled agents (AG1–AG3) running streams under live TPC-C load; new agent version staged on the hub; on AG3, arrange for the staged binary to be corrupted (truncated) after download but before swap — via test hook.

**Steps:**
1. Approve fleet-wide upgrade in the hub UI; record approval audit entry.
2. Observe rolling upgrade: AG1, AG2 swap, health-check, and report the new version.
3. Observe AG3: corrupted binary fails health check.
4. Verify AG3 auto-rolled back to the prior version and its streams resumed.
5. Run compare across all three agents' streams.

**Expected results:** AG1/AG2 upgrade with no job failures beyond a bounded reconnect blip; AG3 rolls back automatically within the health-check window and continues on the old version; no data loss anywhere (compare clean); the hub shows accurate per-agent version state including AG3's rollback event.

**Evidence:** Version states before/after, rollback event log, compare reports, approval audit entry.

### AGT-08 — Mixed-version compatibility window

**Preconditions:** Hub upgraded to version N+1; agents held at version N (within the documented window).

**Steps:**
1. Run one job of each of the four types (capture, integrate, refresh, compare) through a version-N agent under the N+1 hub.
2. Verify results (compare for the data jobs; report generation for the compare job).

**Expected results:** All four job types complete correctly; any deprecation notices are logged but non-fatal.

**Evidence:** Job records, compare reports, log excerpts.

### AGT-09 — Onebox quick-start

**Preconditions:** Single clean host; product install bundle; nothing else.

**Steps:**
1. Execute the published quick-start tutorial verbatim (this procedure doubles as documentation validation): install hub with embedded agent and SQLite repository, enroll nothing (embedded agent auto-registers), create a Postgres→Postgres stream against the bundled lab compose file, activate, generate changes, observe replication, run compare.
2. Time the procedure.

**Expected results:** Tutorial completes start-to-finish with no undocumented steps; compare clean; total time within the tutorial's stated estimate.

**Evidence:** Timed transcript; any documentation discrepancy filed as a doc bug (a discrepancy fails this test).

### AGT-10 — Static binary audit

**Preconditions:** Release Linux artifact from CI.

**Steps:**
1. Run `ldd replagent` on the release binary.
2. Run the linkage audit script (checks for dynamic dependencies, verifies the Oracle-client feature build is the only documented exception and is a separately named artifact).

**Expected results:** `ldd` reports "not a dynamic executable" (or statically linked); audit script passes; artifact names match the documented matrix.

**Evidence:** Command output archived with the release record.

## 11. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| AGT-01 | Fresh host: enrollment with a one-time token establishes pinned mTLS in one command; a reused token is refused |
| AGT-02 | Agent-initiated mode: stream runs end-to-end with zero inbound firewall rules on the agent host (verified by host firewall config) |
| AGT-03 | A non-pinned hub certificate is rejected by an agent configured with a hub allowlist |
| AGT-04 | Source-side filtering under a mixed TPC-C + decoy workload: every unsubscribed change is skipped before decode (parser counters), produces zero pre-encryption frame bytes (diagnostic tap), and adds zero wire volume versus a decoy-free baseline (differential measurement within documented tolerance) |
| AGT-05 | Local spool enabled: hub down for 30 minutes under load — capture continues, spool drains in order on recovery, compare proves zero loss/duplication; disk budget is never exceeded |
| AGT-06 | Local spool disabled (default): hub outage produces the documented stall behavior and alert, and no agent-host disk growth |
| AGT-07 | Orchestrated upgrade across a three-agent fleet under live load: zero data loss; a deliberately corrupted binary triggers automatic rollback on its host only |
| AGT-08 | Mixed-version window: hub at N+1 with agents at N completes all four job types |
| AGT-09 | Onebox install (hub with embedded agent) completes the quick-start tutorial on a single host with SQLite repository |
| AGT-10 | Static binary verification: `ldd` reports no dynamic dependencies on the release Linux artifact (Oracle client feature excepted and documented) |

## 12. Open Questions

The agent-initiated tunnel protocol (long-lived mTLS stream with multiplexing vs reconnect-per-job) needs a design decision with throughput measurements. Default spool budget guidance per source volume tier awaits benchmark data. Whether the Oracle Instant Client dependency can be isolated to an optional dynamically-linked build without forking the artifact matrix is under investigation.
