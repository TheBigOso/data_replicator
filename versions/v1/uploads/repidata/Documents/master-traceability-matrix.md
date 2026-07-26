# Master Traceability Matrix

**Status:** Baselined from the published design specifications on 2026-07-12. No implementation or verification evidence is recorded in this repository yet.

## Purpose and use

This is the authoritative cross-specification register of acceptance criteria. Each row links a requirement to its owning specification and identically numbered test procedure. A row moves to **Pass** only after the procedure has been executed, all expected results observed, and the evidence location recorded. A procedure or design document by itself is not evidence of a pass.

### State definitions

| State | Count | Meaning |
|---|---:|---|
| Not run | 123 | Baselined criterion with a defined procedure; no execution evidence recorded. |
| Gated | 3 | Awaiting a named dependency before it can enter active verification. |
| Deferred (v2) | 2 | Explicitly outside the current v1 scope. |
| Pass / Fail / Inconclusive | 0 | Results available only after a procedure is run and evidence is archived. |

### Evidence and update rules

1. Keep the criterion ID stable; change the owning specification first if the requirement changes.
2. Record a durable evidence location for every completed run (for example, a CI run, compare report, packet capture, or audit-log excerpt).
3. Do not replace a failure or inconclusive result with a pass; add the later run evidence and retain the earlier record.
4. Reconcile this matrix whenever an acceptance-criteria table or test procedure changes.

## Coverage summary

- **165** acceptance criteria across **13** published design specifications.
- **128** identically numbered test procedures, verified by the baseline extraction; the 28 FLT criteria (FLT-01..11 on 2026-07-15, FLT-12..18 on 2026-07-16, FLT-19..23 on 2026-07-17, FLT-24..25 on 2026-07-18, FLT-26..28 on 2026-07-21) and the 9 CON criteria (CON-01..09 on 2026-07-26) are newly added and await procedures.

## Architecture (architecture.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| ARC-01 | End-to-end pipeline (Postgres â†’ file log â†’ Postgres) delivers a TPC-C change stream with source-equals-target proven by compare | ARC-01 | Not run | - |
| ARC-02 | Kill the hub mid-stream: capture and integrate resume from checkpoints on restart with zero loss and zero duplicates | ARC-02 | Not run | - |
| ARC-03 | Broadcast to two targets: file GC occurs only after both integrates acknowledge; deleting one target's ack state halts GC | ARC-03 | Not run | - |
| ARC-04 | Change files on hub disk are unreadable without the payload key (AES-GCM verified); TLS-only capture without payload encryption is not possible in any configuration | ARC-04 | Not run | - |
| ARC-05 | Repository contains zero row-change data after a full benchmark run (schema audit) | ARC-05 | Not run | - |
| ARC-06 | Hub restore from pg_dump plus existing file log resumes all pipelines correctly | ARC-06 | Not run | - |
| ARC-07 | Every UI operation is reproducible via documented REST calls (automated UI-vs-API parity sweep) | ARC-07 | Not run | - |
| ARC-08 | Origin lineage present, complete, and correctly ordered on every record across a cascading two-hop pipeline: hop-2 records carry the two-entry chain whose first entry traces to hop-0 | ARC-08 | Not run | - |
| ARC-09 | Hub start with an expired maintenance term: replication continues; upgrade to a post-entitlement version is refused with a clear message | ARC-09 | Not run | - |
| ARC-10 | cargo-deny gate fails the build on introduction of a GPL-family dependency | ARC-10 | Not run | - |
| ARC-11 | File-target integrate killed mid-cycle (including between data writes and the manifest update) converges on replay to an object set with zero missing and zero duplicate records, identical to an uninterrupted control run | ARC-11 | Not run | - |
| ARC-12 | *(gated on the Kafka connector)* Kafka integrate under repeated mid-transaction kills delivers every source change exactly once to read_committed consumers, resuming position from the state topic | ARC-12 | Gated | - |

| ARC-13 | Held-consumer disk pressure crosses warning, throttle, and admission-refusal thresholds without deleting unacknowledged files, losing source positions, emitting partial files, or exceeding configured spool/storage budgets; recovery drains and compares clean | ARC-13 | Not run | - |
| ARC-14 | A normal repository migration, an injected migration failure, and rollback to a verified pre-upgrade backup preserve the declared schema state, prevent unsafe job dispatch, and converge active pipelines with zero source-to-target divergence | ARC-14 | Not run | - |

## Replication Topologies (replication-topologies.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| TOP-01 | Broadcast to two heterogeneous targets: both receive the identical change stream; compare verifies both against source; GC holds until the slower target acknowledges | TOP-01 | Not run | - |
| TOP-02 | Consolidation of three sources into one Postgres target: state tables remain isolated per pipeline; kill and resume one pipeline without disturbing the other two | TOP-02 | Not run | - |
| TOP-03 | Cascading two-hop chain delivers end-to-end with correct origin markers at each hop; compare verifies hop 2 against hop 0 | TOP-03 | Not run | - |
| TOP-04 | Consolidation naming collision (same table name from two sources) is caught at configuration time, not runtime | TOP-04 | Not run | - |
| TOP-05 | (v2) Bidirectional pair under concurrent bilateral writes: zero loopback re-application over a 1M-change soak run | TOP-05 | Deferred (v2) | - |
| TOP-06 | (v2) Seeded write-write collision is detected, resolved per configured policy, and logged as an event with both images | TOP-06 | Deferred (v2) | - |
| TOP-07 | Topology view renders a broadcast, a consolidation, and a two-hop cascade legibly from live repository state | TOP-07 | Not run | - |

## Location (location.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| LOC-01 | Location creation with insufficient privileges reports the exact missing grants at validation time; no job ever starts against an invalid location | LOC-01 | Not run | - |
| LOC-02 | Credential rotation via external secret reference takes effect on next connection with zero pipeline restarts and zero plaintext appearing in any log (log audit) | LOC-02 | Not run | - |
| LOC-03 | API responses and configuration exports containing a location never include credential material (automated sweep) | LOC-03 | Not run | - |
| LOC-04 | A class capability matrix change (e.g., new slicing type) propagates to both the generated documentation and UI enforcement from the single declaration | LOC-04 | Not run | - |
| LOC-05 | Agentless Oracle location via BFILE completes a capture cycle on a lab RDS-equivalent (no local agent) | LOC-05 | Not run | - |
| LOC-06 | Scheduled-refresh-only location with a SELECT-only account completes a full refresh; attempting to enable CDC on it is refused with the documented privilege list | LOC-06 | Not run | - |
| LOC-07 | Location health probes detect a dropped listener within one probe interval and surface degraded state on the Locations screen and REST API | LOC-07 | Not run | - |

## Agent (agent.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| AGT-01 | Fresh host: enrollment with a one-time token establishes pinned mTLS in one command; a reused token is refused | AGT-01 | Not run | - |
| AGT-02 | Agent-initiated mode: pipeline runs end-to-end with zero inbound firewall rules on the agent host (verified by host firewall config) | AGT-02 | Not run | - |
| AGT-03 | A non-pinned hub certificate is rejected by an agent configured with a hub allowlist | AGT-03 | Not run | - |
| AGT-04 | Source-side filtering under a mixed TPC-C + decoy workload: every unsubscribed change is skipped before decode (parser counters), produces zero pre-encryption frame bytes (diagnostic tap), and adds zero wire volume versus a decoy-free baseline (differential measurement within documented tolerance) | AGT-04 | Not run | - |
| AGT-05 | Local spool enabled: hub down for 30 minutes under load â€” capture continues, spool drains in order on recovery, compare proves zero loss/duplication; disk budget is never exceeded | AGT-05 | Not run | - |
| AGT-06 | Local spool disabled (default): hub outage produces the documented stall behavior and alert, and no agent-host disk growth | AGT-06 | Not run | - |
| AGT-07 | Orchestrated upgrade across a three-agent fleet under live load: zero data loss; a deliberately corrupted binary triggers automatic rollback on its host only | AGT-07 | Not run | - |
| AGT-08 | Mixed-version window: hub at N+1 with agents at N completes all four job types | AGT-08 | Not run | - |
| AGT-09 | Onebox install (hub with embedded agent) completes the quick-start tutorial on a single host with SQLite repository | AGT-09 | Not run | - |
| AGT-10 | Static binary verification: `ldd` reports no dynamic dependencies on the release Linux artifact (Oracle client feature excepted and documented) | AGT-10 | Not run | - |

## Scheduler and Refresh Modes (scheduler.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| SCH-01 | Cron schedule in a DST-observing timezone fires correctly across both DST transitions (simulated clock) | SCH-01 | Not run | - |
| SCH-02 | No job launches inside an active blackout window over a 30-day simulated calendar including edge-aligned triggers | SCH-02 | Not run | - |
| SCH-03 | Blackout beginning mid-run: run-to-completion and checkpoint-and-pause policies each behave as configured | SCH-03 | Not run | - |
| SCH-04 | Overlap policies: a deliberately slow refresh under a fast trigger produces exactly the configured behavior for skip, queue-one, and kill-and-restart | SCH-04 | Not run | - |
| SCH-05 | Retry backoff follows the configured curve; the failure threshold trips exactly one alert and halts retries | SCH-05 | Not run | - |
| SCH-06 | Mode 2 pipeline with a SELECT-only account completes recurring reloads; compare verifies each against source | SCH-06 | Not run | - |
| SCH-07 | Snapshot consistency: refresh under concurrent TPC-C updates yields a target coherent as-of one SCN (cross-table FK audit) | SCH-07 | Not run | - |
| SCH-08 | Stage-and-swap: target readers polling throughout a refresh never observe a missing or partial table; a killed refresh leaves prior data intact | SCH-08 | Not run | - |
| SCH-09 | Mode 3: seeded drift (manual target mutation) is detected by the scheduled compare and alerts within one cycle | SCH-09 | Not run | - |
| SCH-10 | Job state transitions (including HANGING detection on a stalled job) are visible via REST API within one poll interval | SCH-10 | Not run | - |
| SCH-11 | Schedule editor next-run preview matches actual fire times over a week-long simulation | SCH-11 | Not run | - |

## Slicing (slicing-design.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| SLC-01 | Boundary slicing on an indexed numeric key: EXPLAIN shows index range scan per slice; union of slices equals full table exactly (compare-verified); no row appears in two slices | SLC-01 | Not run | - |
| SLC-02 | Histogram-derived boundaries on a skewed key produce slices within Â±15% row-count of each other on the TPC-C corpus with injected skew | SLC-02 | Not run | - |
| SLC-03 | Partition-aligned slicing prunes to exactly the expected partitions (verified via source execution statistics) | SLC-03 | Not run | - |
| SLC-04 | Modulo selection on a table above the size threshold surfaces the full-scan warning; proceeding logs the acknowledgment | SLC-04 | Not run | - |
| SLC-05 | Modulo/hash on a float column or out-of-range NUMBER is refused with the documented explanation | SLC-05 | Not run | - |
| SLC-06 | Date boundary slicing Oracle â†’ Snowflake assigns every row to the correct slice across the type boundary (compare-verified) | SLC-06 | Not run | - |
| SLC-07 | Kill a slice worker mid-transfer: only that slice retries; completed slices are untouched; final compare shows source equals target | SLC-07 | Not run | - |
| SLC-08 | Kill the hub mid-refresh: on recovery, the operation resumes from per-slice checkpoints with zero duplicate rows at the target | SLC-08 | Not run | - |
| SLC-09 | Sliced refresh with one deliberately failing slice never swaps a partial table into the live target; readers see the old data throughout | SLC-09 | Not run | - |
| SLC-10 | All slices of a snapshot-consistent refresh read as-of one SCN (verified against a source workload running concurrent updates) | SLC-10 | Not run | - |
| SLC-11 | Slice map states, metrics, and ETA are served identically via REST API and UI; ETA error under 20% in the second half of a benchmark run | SLC-11 | Not run | - |
| SLC-12 | Drill-in displays the literal executed predicate; pending slices show planned predicates before execution | SLC-12 | Not run | - |
| SLC-13 | Data preview without the data-viewer role is denied; with the role, the access is present in the audit log; with the hub policy disabled, preview is unavailable to all roles | SLC-13 | Not run | - |
| SLC-14 | Advisor recommendation on the lab corpus: EXPLAIN validation catches a seeded full-scan predicate and revises the plan | SLC-14 | Not run | - |
| SLC-15 | Advisor operates fully (recommendation + structured explanation) with the AI layer disabled and no external connectivity | SLC-15 | Not run | - |
| SLC-16 | Rowid-range slicing on a 10M+ row lab table balances slices within Â±10% by blocks and requires no index | SLC-16 | Not run | - |
| SLC-17 | Parallel writers on a staging target increase load throughput measurably versus single writer on the benchmark corpus, with correctness compare-verified | SLC-17 | Not run | - |

## Channel (channel.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| CHA-01 | Invalid channel definitions are refused at save time with field-level messages; no partial definitions persist | CHA-01 | Not run | - |
| CHA-02 | A CLI-exported definition applied to a clean hub yields byte-equivalent effective behavior (state diff empty; identical DML produces identical targets) | CHA-02 | Not run | - |
| CHA-03 | Standard replica mirrors the scripted DML exactly (compare-verified; deletes physically applied) | CHA-03 | Not run | - |
| CHA-04 | Soft delete marks every source delete on the target with configured columns; zero physical target deletes; documented re-insert behavior | CHA-04 | Not run | - |
| CHA-05 | TimeKey produces a correct, append-only, metadata-complete audit trail matching the published spec | CHA-05 | Not run | - |
| CHA-06 | Mixed per-table styles within one channel materialize independently with no bleed-through | CHA-06 | Not run | - |
| CHA-07 | *(gated on the ddl-capture design pass)* DDL policies (adapt / hold-and-alert) behave per configuration at channel and table level; held changes apply cleanly on approval | CHA-07 | Gated | - |
| CHA-08 | Zero-downtime activation under full load: compare clean across the refresh/capture boundary | CHA-08 | Not run | - |
| CHA-09 | Pause holds checkpoints with zero data movement; resume is loss/duplicate-free; retirement leaves no file residue and a retained definition history | CHA-09 | Not run | - |
| CHA-10 | Every definition change is versioned with actor, timestamp, and diff across UI, API, and GitOps paths | CHA-10 | Not run | - |
| CHA-11 | Activation plans are minimal and auto-scoped: a change touching N tables produces steps for exactly those tables and affected locations | CHA-11 | Not run | - |
| CHA-12 | State-table recreation requires typed destructive confirmation; a plan combining recreation with recovery rewind is rejected by the planner | CHA-12 | Not run | - |
| CHA-13 | Burst tables are never dropped mid-cycle without explicit force; the default plan waits for cycle drain | CHA-13 | Not run | - |
| CHA-14 | Enrollment is per-table incremental; a 3-table change on a 200-table channel re-enrolls exactly 3 tables | CHA-14 | Not run | - |
| CHA-15 | Supplemental logging is granular per spec, parallel across locations, no-op on unchanged re-activation, and never dropped on deactivation | CHA-15 | Not run | - |
| CHA-16 | Capture-start and emit-time combinations behave exactly as specified against long-running and boundary-committed transactions, with log-availability prechecked | CHA-16 | Not run | - |
| CHA-17 | A destroyed hub is rebuilt and resumes via recovery rewind to the target integrate sequence with zero loss and zero duplicates | CHA-17 | Not run | - |
| CHA-18 | Post-activation refresh honors every table-creation policy exactly (create-missing, alter/recreate, keep-structure, keep-old-rows), compare-verified | CHA-18 | Not run | - |
| CHA-19 | Replication key selection follows the hierarchy exactly across the key fixture set, with provenance and implicit-key badges displayed identically in UI and API | CHA-19 | Not run | - |
| CHA-20 | Implicit-key tables execute updates as delete+insert and deletes as single-row-limited statements; one of N identical rows is removed, compare-verified | CHA-20 | Not run | - |
| CHA-21 | The no-duplicate-rows guardrail refuses, warns, or accepts per policy; the accepted fast path is observable in the target statement audit | CHA-21 | Not run | - |
| CHA-22 | *(gated on the first distributed-target connector)* Distribution keys derive and validate per spec; staging and target tables always share the distribution key; per-target limits enforced at definition time | CHA-22 | Gated | - |
| CHA-23 | Table groups assign per spec (auto-by-schema, GENERAL default, one group per table); the settings ladder resolves as documented with correct provenance in UI and API; group mappings land data correctly | CHA-23 | Not run | - |
| CHA-24 | Identity derivation follows the published normalization rules with accurate badges; collisions refused at definition time; rename, schema, and fan-out mappings land data correctly; identity persists across physical renames | CHA-24 | Not run | - |

## Refresh (refresh.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| REF-01 | Bulk refresh is compare-clean with atomic swap; readers never observe partial state; a killed run leaves prior data live | REF-01 | Not run | - |
| REF-02 | Targets without native bulk interfaces load via the documented staging lifecycle with zero residue | REF-02 | Not run | - |
| REF-03 | Refresh data carries identical file-log guarantees to CDC (encryption, sequencing, authentication) | REF-03 | Not run | - |
| REF-04 | Online refresh under full load loses nothing and double-applies nothing at the snapshot boundary, with boundaries auditable in the run record | REF-04 | Not run | - |
| REF-05 | Row-wise repair touches O(drift) rows, never O(table); re-compare clean | REF-05 | Not run | - |
| REF-06 | Row-wise and bulk refresh converge a drifted target to identical, source-equal states | REF-06 | Not run | - |
| REF-07 | Filtered-scope refresh repairs exactly inside the predicate fence | REF-07 | Not run | - |
| REF-08 | Ad-hoc refreshes follow acyclic scheduler semantics identically from UI and CLI | REF-08 | Not run | - |
| REF-09 | Integrate is never suspended by a refresh: non-refreshed tables replicate with flat latency throughout a scoped online refresh, and a killed refresh leaves no blocking state â€” the rerun needs no manual cleanup | REF-09 | Not run | - |

## Compare (compare.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| CMP-01 | Verified-identical data yields zero differences from bulk, row-wise, and composed compare | CMP-01 | Not run | - |
| CMP-02 | Every seeded difference is found and correctly classified, matching an external oracle exactly; nothing unseeded is reported | CMP-02 | Not run | - |
| CMP-03 | One hour of online compares under full-rate replication confirms zero false positives while catching an injected real difference | CMP-03 | Not run | - |
| CMP-04 | Repair from a report converges the target (re-compare clean) with writes proportional to differences | CMP-04 | Not run | - |
| CMP-05 | Bulk block localization is exact and all methods agree, including on hash-collision fixtures | CMP-05 | Not run | - |
| CMP-06 | The heterogeneous type-gap corpus compares clean per the published canonicalization table, while real mutations in every type family are still caught | CMP-06 | Not run | - |
| CMP-07 | Exclusions and tolerances are honored, recorded in the report, and never mask unrelated differences | CMP-07 | Not run | - |
| CMP-08 | Scheduled compares alert on drift within one cycle with linked, retained reports; a killed compare resumes to an identical report | CMP-08 | Not run | - |
| CMP-09 | The daily sync report's every figure (rows, columns, match rate, activity, verdict) matches external ground truth across in-sync, drifted, and structure-mismatch channels | CMP-09 | Not run | - |
| CMP-10 | Reports deliver identically to UI, email, webhook, and file drop; the file-drop path works fully air-gapped with zero egress | CMP-10 | Not run | - |
| CMP-11 | On-demand compares emit the identical report format from UI and CLI and are archived alongside scheduled reports | CMP-11 | Not run | - |
| CMP-12 | Structure mismatches short-circuit data compare with the discrepancy named; declared extras pass, undeclared extras flag | CMP-12 | Not run | - |
| CMP-13 | Direct file compare produces an oracle-exact inventory via sliced prereaders with encrypted, cleaned intermediates; unsupported channel styles are refused as documented | CMP-13 | Not run | - |
| CMP-14 | Multi-target compare reads the source once and delivers independent per-target verdicts | CMP-14 | Not run | - |

## Jobs (jobs.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| JOB-01 | Every documented state transition is observable via API within one poll interval with a caused event; undocumented transitions are refused â€” the published diagram is closed | JOB-01 | Not run | - |
| JOB-02 | Cyclic jobs cycle PENDINGâ†”RUNNING without terminal states; acyclic jobs terminate with queryable history | JOB-02 | Not run | - |
| JOB-03 | Event-driven tasks return an event ID immediately, report truthful structured progress, and attach their artifacts on completion, identically via UI, CLI, and API | JOB-03 | Not run | - |
| JOB-04 | Cancellation stops work at a checkpoint boundary with cause recorded, prior data intact, and clean convergence on rerun | JOB-04 | Not run | - |
| JOB-05 | Suspend is checkpoint-clean and resumable; disable refuses ordinary resume until explicit re-enable; compare clean throughout | JOB-05 | Not run | - |
| JOB-06 | Every run has a complete, accurate, retained structured log; the alert â†’ run â†’ event â†’ artifact chain resolves at every link | JOB-06 | Not run | - |
| JOB-07 | Run-now behaves identically from all three surfaces and obeys the overlap policy without privileged bypass | JOB-07 | Not run | - |
| JOB-08 | Priority classes and resource caps (agent concurrency, slice parallelism) are enforced as observed, with settings provenance displayed | JOB-08 | Not run | - |

## Events (events.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| EVT-01 | Every state-changing API call produces exactly one audit event and read-only calls produce none, proven by a whole-surface sweep that fails CI on uncovered endpoints | EVT-01 | Not run | - |
| EVT-02 | The ledger is append-only with retention as the sole, itself-evented removal mechanism; event IDs are strictly monotonic under concurrency | EVT-02 | Not run | - |
| EVT-03 | The unified timeline answers scripted multi-actor scenarios exactly under every filter combination (class, actor, scope, time) | EVT-03 | Not run | - |
| EVT-04 | Same-job pending events are superseded with the successor named; interrupted task events resume from checkpoint with visible history and identical final artifacts | EVT-04 | Not run | - |
| EVT-05 | Syslog, webhook, and file-drop forwarders deliver every event with dedupable IDs; gaps are detected and alerted; file drop works fully air-gapped | EVT-05 | Not run | - |
| EVT-06 | Actors are attributed precisely across UI users, API tokens, and GitOps commit references | EVT-06 | Not run | - |
| EVT-07 | Event scope (repository, hub, channel, locations, tables) is recorded and queryable exactly | EVT-07 | Not run | - |

## Fleet Hierarchy & Admin Model (fleet-hierarchy.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| FLT-01 | The Global Fleet console lists every enrolled fleet and its virtual fleets with state, pipeline/connection/user counts, and P95 latency, from live feeds | FLT-01 | Not run | - |
| FLT-02 | The console is visible only to holders of `FleetViewer` (or `SuperAdmin`); all others receive the locked screen and no fleet metadata over the API | FLT-02 | Not run | - |
| FLT-03 | Virtual fleets where the viewer holds no grant render as name-and-state summaries with counts masked, in UI and API alike | FLT-03 | Not run | - |
| FLT-04 | Console search matches fleet, division, and virtual-fleet names; state filter and error-first sort behave correctly at 200+ fleets without pagination stalls | FLT-04 | Not run | - |
| FLT-05 | Sidebar pinning persists per user; unpinned fleets are reachable only via the console | FLT-05 | Not run | - |
| FLT-06 | Fleet creation is refused for non-Global Admins; on success the fleet enters Enrolling state, the creator holds its first Fleet Admin grant, and both are ledger events | FLT-06 | Not run | - |
| FLT-07 | Virtual-fleet isolation: pipelines, connections, users, and grants of one virtual fleet are invisible and inoperable from a sibling virtual fleet for a user scoped to the sibling | FLT-07 | Not run | - |
| FLT-08 | Downward-only admin editing is enforced server-side: a Fleet Admin cannot alter repository-wide grants; a VF Admin cannot alter grants outside their virtual fleet — attempts fail and are evented | FLT-08 | Not run | - |
| FLT-09 | SuperAdmin can edit any grant except their own SuperAdmin grant, which only another SuperAdmin can revoke | FLT-09 | Not run | - |
| FLT-10 | The Permissions surface is one-row-per-attachment: a user granted on N scopes appears exactly N times with correct fleet/virtual-fleet resolution; Users remains one-row-per-account | FLT-10 | Not run | - |
| FLT-11 | The user list each admin level sees is derived from grants (global → everyone; fleet → accounts attached to the fleet; VF → accounts attached to the virtual fleet) and matches the API's answer | FLT-11 | Not run | - |
| FLT-12 | The Permissions view is scoped like the user list: a Fleet Admin sees only grants within their fleet (repository-wide grants visible read-only); a VF Admin only their virtual fleet's; scoping identical in UI and API | FLT-12 | Not run | - |
| FLT-13 | Users and Permissions tables sort on every column, ascending/descending, with recency-ordered "last active" and a stable default (user, ascending) | FLT-13 | Not run | - |
| FLT-14 | A signed-in user can edit only their own full name and email; username and authentication method remain admin-managed; every profile change is a ledger event | FLT-14 | Not run | - |
| FLT-15 | Environment (color + label) resolves per user × per fleet; virtual fleets and pipelines inherit their fleet's environment; the Global console renders the neutral non-renamable banner | FLT-15 | Not run | - |
| FLT-16 | Banner renaming is prompt-guarded (pencil icon or environment change raises Edit name / Keep); the label is read-only until editing is confirmed; each color retains its own label | FLT-16 | Not run | - |
| FLT-17 | Entering a Production-environment fleet forces dark mode; the manual toggle covers non-production; all controls remain readable in both themes | FLT-17 | Not run | - |
| FLT-18 | Theming choices (per-fleet colors, per-color labels, dark mode, banner visibility) persist per user across sessions and are isolated between users | FLT-18 | Not run | - |
| FLT-19 | Sign-in is by email address (no usernames) and routes the user to the highest scope their grants reach (global grant → Global Fleet console; fleet grant → Fleet view; VF grant → that Virtual Fleet; none → read-only Global); disabled and unknown accounts are refused | FLT-19 | Not run | - |
| FLT-20 | The signed-in session persists across page reloads; Sign out clears it and returns to the sign-in screen with no residual access | FLT-20 | Not run | - |
| FLT-21 | Self-service profile edits (full name, email) propagate immediately to every identity surface (chip, menu, Users table) and persist per account across reloads and re-sign-in | FLT-21 | Not run | - |
| FLT-22 | Locally created users (full name + unique email, no username) receive a starter ReadOnly grant on the creation scope plus All Users defaults, persist across sessions, and can sign in immediately with their email | FLT-22 | Not run | - |
| FLT-23 | Sidebar width is user-resizable (180–440 px) and persists per user with their other workspace preferences | FLT-23 | Not run | - |
| FLT-24 | Admins can edit any user's full name and email from the Users table; edits propagate immediately to every surface and persist across reloads; duplicate emails are rejected | FLT-24 | Not run | - |
| FLT-25 | Full names are the primary identity across the console (user chip, Users table, Permissions rows, grant dialog); email is the secondary identifier; no usernames surface in the UI | FLT-25 | Not run | - |
| FLT-26 | Connections view shows Connection (with role), Platform, Description, Agent, Heartbeat, and Status, plus a per-row Test action reporting pass/fail with latency or failure cause | FLT-26 | Not run | - |
| FLT-27 | Every Connections column is sortable (asc/desc toggle with visible indicator; default Connection descending shown on load) and filterable via combining per-column filter boxes; numeric columns sort numerically | FLT-27 | Not run | - |
| FLT-28 | Connections column chooser adds/removes columns (Host/endpoint, Created, Created by, Pipelines, Last test; Test button hideable; Connection locked); visibility and sort persist per user and are isolated between users | FLT-28 | Not run | - |

## Connections (connections.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| CON-01 | The connections list shows Connection (with source/target role), Platform, Description, Agent, Heartbeat, and Status, plus a per-row test action that reports pass with latency or fail with cause | CON-01 | Not run | - |
| CON-02 | Every visible column is sortable, toggling ascending/descending with a visible indicator; the default order is Connection descending with the indicator shown on load; Heartbeat and Pipelines sort numerically | CON-02 | Not run | - |
| CON-03 | Per-column filter boxes combine across columns and show an explicit empty state; column visibility and sort order persist per user across sessions and never leak between users | CON-03 | Not run | - |
| CON-04 | The column chooser adds and removes columns including Host/endpoint, Created, Created by, Pipelines, and Last test; the Test action is hideable; the Connection column cannot be hidden | CON-04 | Not run | - |
| CON-05 | Connection detail shows agent mode (agent-based with host, port, binary, and heartbeat, or agentless), database connection, resolved source/target properties, and pipeline membership with the role played in each pipeline | CON-05 | Not run | - |
| CON-06 | The agent dialog switches between agent and agentless, exposes agent host and port, tests the agent (reachability, latency, mTLS, certificate, version match), and supports certificate rotation and single-use enrollment token re-issue | CON-06 | Not run | - |
| CON-07 | The Oracle database dialog exposes ORACLE_HOME and a local-SID or TNS connect path; a saved TNS string re-derives host, port, and service consistently across the console | CON-07 | Not run | - |
| CON-08 | Capture and integrate method choices are constrained to what the class supports, and Direct redo requested over a non-loopback TNS connection raises a configuration-time warning naming the loopback or local-SID requirement | CON-08 | Not run | - |
| CON-09 | Every configuration dialog defaults to testing before saving, allows saving untested, discloses in the confirmation which of the two occurred, and records the save in the event ledger | CON-09 | Not run | - |
