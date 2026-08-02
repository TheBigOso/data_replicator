# Master Traceability Matrix

**Status:** Baselined from the published design specifications on 2026-07-12; console-surface and path-model criteria added 2026-08-01. No implementation or verification evidence is recorded in this repository yet.

## Purpose and use

This is the authoritative cross-specification register of acceptance criteria. Each row links a requirement to its owning specification and identically numbered test procedure. A row moves to **Pass** only after the procedure has been executed, all expected results observed, and the evidence location recorded. A procedure or design document by itself is not evidence of a pass.

### State definitions

| State | Count | Meaning |
|---|---:|---|
| Not run | 267 | Baselined criterion with a defined procedure; no execution evidence recorded. |
| Gated | 7 | Awaiting a named dependency before it can enter active verification. |
| Deferred (v2) | 2 | Explicitly outside the current v1 scope. |
| Pass / Fail / Inconclusive | 0 | Results available only after a procedure is run and evidence is archived. |

### Evidence and update rules

1. Keep the criterion ID stable; change the owning specification first if the requirement changes.
2. Record a durable evidence location for every completed run (for example, a CI run, compare report, packet capture, or audit-log excerpt).
3. Do not replace a failure or inconclusive result with a pass; add the later run evidence and retain the earlier record.
4. Reconcile this matrix whenever an acceptance-criteria table or test procedure changes.

## Coverage summary

- **173** acceptance criteria across **13** published design specifications.
- **128** identically numbered test procedures, verified by the baseline extraction; the 28 FLT criteria (FLT-01..11 on 2026-07-15, FLT-12..18 on 2026-07-16, FLT-19..23 on 2026-07-17, FLT-24..25 on 2026-07-18, FLT-26..28 on 2026-07-21) the 31 FLT criteria (FLT-29..31 added 2026-07-26) and the 14 CON criteria (CON-01..09 on 2026-07-26, CON-10..14 on 2026-07-26) are newly added and await procedures.

## Architecture (architecture.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| ARC-01 | End-to-end stream (Postgres â†’ file log â†’ Postgres) delivers a TPC-C change stream with source-equals-target proven by compare | ARC-01 | Not run | - |
| ARC-02 | Kill the hub mid-stream: capture and integrate resume from checkpoints on restart with zero loss and zero duplicates | ARC-02 | Not run | - |
| ARC-03 | Broadcast to two targets: file GC occurs only after both integrates acknowledge; deleting one target's ack state halts GC | ARC-03 | Not run | - |
| ARC-04 | Change files on hub disk are unreadable without the payload key (AES-GCM verified); TLS-only capture without payload encryption is not possible in any configuration | ARC-04 | Not run | - |
| ARC-05 | Repository contains zero row-change data after a full benchmark run (schema audit) | ARC-05 | Not run | - |
| ARC-06 | Hub restore from pg_dump plus existing file log resumes all streams correctly | ARC-06 | Not run | - |
| ARC-07 | Every UI operation is reproducible via documented REST calls (automated UI-vs-API parity sweep) | ARC-07 | Not run | - |
| ARC-08 | Origin lineage present, complete, and correctly ordered on every record across a cascading two-hop stream: hop-2 records carry the two-entry chain whose first entry traces to hop-0 | ARC-08 | Not run | - |
| ARC-09 | Hub start with an expired maintenance term: replication continues; upgrade to a post-entitlement version is refused with a clear message | ARC-09 | Not run | - |
| ARC-10 | cargo-deny gate fails the build on introduction of a GPL-family dependency | ARC-10 | Not run | - |
| ARC-11 | File-target integrate killed mid-cycle (including between data writes and the manifest update) converges on replay to an object set with zero missing and zero duplicate records, identical to an uninterrupted control run | ARC-11 | Not run | - |
| ARC-12 | *(gated on the Kafka connector)* Kafka integrate under repeated mid-transaction kills delivers every source change exactly once to read_committed consumers, resuming position from the state topic | ARC-12 | Gated | - |

| ARC-13 | Held-consumer disk pressure crosses warning, throttle, and admission-refusal thresholds without deleting unacknowledged files, losing source positions, emitting partial files, or exceeding configured spool/storage budgets; recovery drains and compares clean | ARC-13 | Not run | - |
| ARC-14 | A normal repository migration, an injected migration failure, and rollback to a verified pre-upgrade backup preserve the declared schema state, prevent unsafe job dispatch, and converge active streams with zero source-to-target divergence | ARC-14 | Not run | - |

## Replication Topologies (replication-topologies.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| TOP-01 | Broadcast to two heterogeneous targets: both receive the identical change stream; compare verifies both against source; GC holds until the slower target acknowledges | TOP-01 | Not run | - |
| TOP-02 | Consolidation of three sources into one Postgres target: state tables remain isolated per stream; kill and resume one stream without disturbing the other two | TOP-02 | Not run | - |
| TOP-03 | Cascading two-hop chain delivers end-to-end with correct origin markers at each hop; compare verifies hop 2 against hop 0 | TOP-03 | Not run | - |
| TOP-04 | Consolidation naming collision (same table name from two sources) is caught at configuration time, not runtime | TOP-04 | Not run | - |
| TOP-05 | (v2) Bidirectional pair under concurrent bilateral writes: zero loopback re-application over a 1M-change soak run | TOP-05 | Deferred (v2) | - |
| TOP-06 | (v2) Seeded write-write collision is detected, resolved per configured policy, and logged as an event with both images | TOP-06 | Deferred (v2) | - |
| TOP-07 | Topology view renders a broadcast, a consolidation, and a two-hop cascade legibly from live repository state | TOP-07 | Not run | - |

## Location (connection.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| LOC-01 | Location creation with insufficient privileges reports the exact missing grants at validation time; no job ever starts against an invalid location | LOC-01 | Not run | - |
| LOC-02 | Credential rotation via external secret reference takes effect on next connection with zero stream restarts and zero plaintext appearing in any log (log audit) | LOC-02 | Not run | - |
| LOC-03 | API responses and configuration exports containing a location never include credential material (automated sweep) | LOC-03 | Not run | - |
| LOC-04 | A class capability matrix change (e.g., new slicing type) propagates to both the generated documentation and UI enforcement from the single declaration | LOC-04 | Not run | - |
| LOC-05 | Agentless Oracle location via BFILE completes a capture cycle on a lab RDS-equivalent (no local agent) | LOC-05 | Not run | - |
| LOC-06 | Scheduled-refresh-only location with a SELECT-only account completes a full refresh; attempting to enable CDC on it is refused with the documented privilege list | LOC-06 | Not run | - |
| LOC-07 | Location health probes detect a dropped listener within one probe interval and surface degraded state on the Locations screen and REST API | LOC-07 | Not run | - |

## Agent (agent.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| AGT-01 | Fresh host: enrollment with a one-time token establishes pinned mTLS in one command; a reused token is refused | AGT-01 | Not run | - |
| AGT-02 | Agent-initiated mode: stream runs end-to-end with zero inbound firewall rules on the agent host (verified by host firewall config) | AGT-02 | Not run | - |
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
| SCH-06 | Mode 2 stream with a SELECT-only account completes recurring reloads; compare verifies each against source | SCH-06 | Not run | - |
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

## Stream (stream.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| STR-01 | Invalid stream definitions are refused at save time with field-level messages; no partial definitions persist | STR-01 | Not run | - |
| STR-02 | A CLI-exported definition applied to a clean hub yields byte-equivalent effective behavior (state diff empty; identical DML produces identical targets) | STR-02 | Not run | - |
| STR-03 | Standard replica mirrors the scripted DML exactly (compare-verified; deletes physically applied) | STR-03 | Not run | - |
| STR-04 | Soft delete marks every source delete on the target with configured columns; zero physical target deletes; documented re-insert behavior | STR-04 | Not run | - |
| STR-05 | TimeKey produces a correct, append-only, metadata-complete audit trail matching the published spec | STR-05 | Not run | - |
| STR-06 | Mixed per-table styles within one stream materialize independently with no bleed-through | STR-06 | Not run | - |
| STR-07 | *(gated on the ddl-capture design pass)* DDL policies (adapt / hold-and-alert) behave per configuration at stream and table level; held changes apply cleanly on approval | STR-07 | Gated | - |
| STR-08 | Zero-downtime activation under full load: compare clean across the refresh/capture boundary | STR-08 | Not run | - |
| STR-09 | Pause holds checkpoints with zero data movement; resume is loss/duplicate-free; retirement leaves no file residue and a retained definition history | STR-09 | Not run | - |
| STR-10 | Every definition change is versioned with actor, timestamp, and diff across UI, API, and GitOps paths | STR-10 | Not run | - |
| STR-11 | Activation plans are minimal and auto-scoped: a change touching N tables produces steps for exactly those tables and affected locations | STR-11 | Not run | - |
| STR-12 | State-table recreation requires typed destructive confirmation; a plan combining recreation with recovery rewind is rejected by the planner | STR-12 | Not run | - |
| STR-13 | Burst tables are never dropped mid-cycle without explicit force; the default plan waits for cycle drain | STR-13 | Not run | - |
| STR-14 | Enrollment is per-table incremental; a 3-table change on a 200-table stream re-enrolls exactly 3 tables | STR-14 | Not run | - |
| STR-15 | Supplemental logging is granular per spec, parallel across locations, no-op on unchanged re-activation, and never dropped on deactivation | STR-15 | Not run | - |
| STR-16 | Capture-start and emit-time combinations behave exactly as specified against long-running and boundary-committed transactions, with log-availability prechecked | STR-16 | Not run | - |
| STR-17 | A destroyed hub is rebuilt and resumes via recovery rewind to the target integrate sequence with zero loss and zero duplicates | STR-17 | Not run | - |
| STR-18 | Post-activation refresh honors every table-creation policy exactly (create-missing, alter/recreate, keep-structure, keep-old-rows), compare-verified | STR-18 | Not run | - |
| STR-19 | Replication key selection follows the hierarchy exactly across the key fixture set, with provenance and implicit-key badges displayed identically in UI and API | STR-19 | Not run | - |
| STR-20 | Implicit-key tables execute updates as delete+insert and deletes as single-row-limited statements; one of N identical rows is removed, compare-verified | STR-20 | Not run | - |
| STR-21 | The no-duplicate-rows guardrail refuses, warns, or accepts per policy; the accepted fast path is observable in the target statement audit | STR-21 | Not run | - |
| STR-22 | *(gated on the first distributed-target connector)* Distribution keys derive and validate per spec; staging and target tables always share the distribution key; per-target limits enforced at definition time | STR-22 | Gated | - |
| STR-23 | Table groups assign per spec (auto-by-schema, GENERAL default, one group per table); the settings ladder resolves as documented with correct provenance in UI and API; group mappings land data correctly | STR-23 | Not run | - |
| STR-24 | Identity derivation follows the published normalization rules with accurate badges; collisions refused at definition time; rename, schema, and fan-out mappings land data correctly; identity persists across physical renames | STR-24 | Not run | - |

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
| CMP-09 | The daily sync report's every figure (rows, columns, match rate, activity, verdict) matches external ground truth across in-sync, drifted, and structure-mismatch streams | CMP-09 | Not run | - |
| CMP-10 | Reports deliver identically to UI, email, webhook, and file drop; the file-drop path works fully air-gapped with zero egress | CMP-10 | Not run | - |
| CMP-11 | On-demand compares emit the identical report format from UI and CLI and are archived alongside scheduled reports | CMP-11 | Not run | - |
| CMP-12 | Structure mismatches short-circuit data compare with the discrepancy named; declared extras pass, undeclared extras flag | CMP-12 | Not run | - |
| CMP-13 | Direct file compare produces an oracle-exact inventory via sliced prereaders with encrypted, cleaned intermediates; unsupported stream styles are refused as documented | CMP-13 | Not run | - |
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
| EVT-07 | Event scope (repository, hub, stream, locations, tables) is recorded and queryable exactly | EVT-07 | Not run | - |

## Fleet Hierarchy & Admin Model (fleet-hierarchy.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| FLT-01 | The Global Fleet console lists every enrolled fleet and its virtual fleets with state, stream/connection/user counts, and P95 latency, from live feeds | FLT-01 | Not run | - |
| FLT-02 | The console is visible only to holders of `FleetViewer` (or `SuperAdmin`); all others receive the locked screen and no fleet metadata over the API | FLT-02 | Not run | - |
| FLT-03 | Virtual fleets where the viewer holds no grant render as name-and-state summaries with counts masked, in UI and API alike | FLT-03 | Not run | - |
| FLT-04 | Console search matches fleet, division, and virtual-fleet names; state filter and error-first sort behave correctly at 200+ fleets without pagination stalls | FLT-04 | Not run | - |
| FLT-05 | Sidebar pinning persists per user; unpinned fleets are reachable only via the console | FLT-05 | Not run | - |
| FLT-06 | Fleet creation is refused for non-Global Admins; on success the fleet enters Enrolling state, the creator holds its first Fleet Admin grant, and both are ledger events | FLT-06 | Not run | - |
| FLT-07 | Virtual-fleet isolation: streams, connections, users, and grants of one virtual fleet are invisible and inoperable from a sibling virtual fleet for a user scoped to the sibling | FLT-07 | Not run | - |
| FLT-08 | Downward-only admin editing is enforced server-side: a Fleet Admin cannot alter repository-wide grants; a VF Admin cannot alter grants outside their virtual fleet — attempts fail and are evented | FLT-08 | Not run | - |
| FLT-09 | SuperAdmin can edit any grant except their own SuperAdmin grant, which only another SuperAdmin can revoke | FLT-09 | Not run | - |
| FLT-10 | The Permissions surface is one-row-per-attachment: a user granted on N scopes appears exactly N times with correct fleet/virtual-fleet resolution; Users remains one-row-per-account | FLT-10 | Not run | - |
| FLT-11 | The user list each admin level sees is derived from grants (global → everyone; fleet → accounts attached to the fleet; VF → accounts attached to the virtual fleet) and matches the API's answer | FLT-11 | Not run | - |
| FLT-12 | The Permissions view is scoped like the user list: a Fleet Admin sees only grants within their fleet (repository-wide grants visible read-only); a VF Admin only their virtual fleet's; scoping identical in UI and API | FLT-12 | Not run | - |
| FLT-13 | Users and Permissions tables sort on every column, ascending/descending, with recency-ordered "last active" and a stable default (user, ascending) | FLT-13 | Not run | - |
| FLT-14 | A signed-in user can edit only their own full name and email; username and authentication method remain admin-managed; every profile change is a ledger event | FLT-14 | Not run | - |
| FLT-15 | Environment (color + label) resolves per user × per fleet; virtual fleets and streams inherit their fleet's environment; the Global console renders the neutral non-renamable banner | FLT-15 | Not run | - |
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
| FLT-28 | Connections column chooser adds/removes columns (Host/endpoint, Created, Created by, Streams, Last test; Test button hideable; Connection locked); visibility and sort persist per user and are isolated between users | FLT-28 | Not run | - |
| FLT-29 | Connections, Jobs, and Events are virtual-fleet screens; Tables, Monitoring, and Admin are stream screens; a virtual fleet lists its streams alphabetically, then Jobs, Events, Connections | FLT-29 | Not run | - |
| FLT-30 | Browser Back and Forward walk the console's screens and never leave the application; filters, modals, and toasts create no history entries | FLT-30 | Not run | - |
| FLT-31 | Fleet and virtual-fleet enterability is grant-derived everywhere it is shown; a SuperAdmin reaches all, an ungranted operator is told which grant to ask for | FLT-31 | Not run | - |

## Connections (connection.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| CON-01 | The connections list shows Connection (with source/target role), Platform, Description, Agent, Heartbeat, and Status, plus a per-row test action that reports pass with latency or fail with cause | CON-01 | Not run | - |
| CON-02 | Every visible column is sortable, toggling ascending/descending with a visible indicator; the default order is Connection descending with the indicator shown on load; Heartbeat and Streams sort numerically | CON-02 | Not run | - |
| CON-03 | Per-column filter boxes combine across columns and show an explicit empty state; column visibility and sort order persist per user across sessions and never leak between users | CON-03 | Not run | - |
| CON-04 | The column chooser adds and removes columns including Host/endpoint, Created, Created by, Streams, and Last test; the Test action is hideable; the Connection column cannot be hidden | CON-04 | Not run | - |
| CON-05 | Connection detail shows agent mode (agent-based with host, port, binary, and heartbeat, or agentless), database connection, resolved source/target properties, and stream membership with the role played in each stream | CON-05 | Not run | - |
| CON-06 | The agent dialog switches between agent and agentless, exposes agent host and port, tests the agent (reachability, latency, mTLS, certificate, version match), and supports certificate rotation and single-use enrollment token re-issue | CON-06 | Not run | - |
| CON-07 | The Oracle database dialog exposes ORACLE_HOME and a local-SID or TNS connect path; a saved TNS string re-derives host, port, and service consistently across the console | CON-07 | Not run | - |
| CON-08 | Capture and integrate method choices are constrained to what the class supports, and Direct redo requested over a non-loopback TNS connection raises a configuration-time warning naming the loopback or local-SID requirement | CON-08 | Not run | - |
| CON-09 | Every configuration dialog defaults to testing before saving, allows saving untested, discloses in the confirmation which of the two occurred, and records the save in the event ledger | CON-09 | Not run | - |
| CON-10 | Connections are created through a five-step wizard whose completed steps collapse to editable summaries | CON-10 | Not run | - |
| CON-11 | A connection can be saved without attaching it to any stream; unattached is the default and it can be attached later | CON-11 | Not run | - |
| CON-12 | Creation refuses a missing or duplicate name and a missing capture/integrate method, naming the reason and returning to the offending step | CON-12 | Not run | - |
| CON-13 | Every value entered during creation is stored and displayed; no field substitutes a derived default for a blank, and editing a blank field opens empty | CON-13 | Not run | - |
| CON-14 | Connections, Jobs, and Events are virtual-fleet screens and Tables, Monitoring, and Admin are stream screens, each scoped to the level opened from, with counts matching the screens they open | CON-14 | Not run | - |

## Console surfaces and path model — baselined 2026-08-01

Criteria below are design-stage rows from the console-surface specifications and the path model. Rows marked *(planned)* in their spec enter as **Gated** on their feature landing in the prototype-to-product transition; all others enter as **Not run**, per the standing rules.

### Global Fleet Console (global-fleet/global-fleet-ui.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| GFC-1 | Console is gated by FleetViewer; without it a locked explainer renders; with it, only granted fleets appear (empty state otherwise) | GFC-1 | Not run | - |
| GFC-2 | Six KPI tiles compute over visible fleets; Attention, Worst P95 > 60 s, and VF-error counts render in danger red | GFC-2 | Not run | - |
| GFC-3 | Triage strip rows carry severity, breadcrumb, title, detail, and raised date+time with relative age, in fixed-width columns that never reflow on live ticks | GFC-3 | Not run | - |
| GFC-4 | Triage ordering is deterministic (rank, then name) — live metric wobble never reorders or re-admits rows | GFC-4 | Not run | - |
| GFC-5 | Every triage row deep-links to the exact problem surface with fleet/VF context switched | GFC-5 | Not run | - |
| GFC-6 | Fleet rows sort triage-first with red left edge and ⚠ concern badge; expanded rows list VFs with per-VF stats and access; Switch appears only where granted | GFC-6 | Not run | - |
| GFC-7 | Search + state filter compose; shown-count updates; pins persist per user | GFC-7 | Not run | - |
| GFC-8 | Global log tails global.out (all fleets merged, time-ordered), filterable, and opens in the floating overlay viewer | GFC-8 | Not run | - |
| GFC-9 | Console is read-only across systems — every mutating action requires switching into the owning fleet/VF first | GFC-9 | Not run | - |

### Fleet Console (fleet/fleet-ui.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| FLC-1 | The page opens for any grant reaching the fleet; fleets with no reaching grant are absent from the tree and the global matrix | FLC-1 | Not run | - |
| FLC-2 | ⚙ Fleet Admin and New virtual fleet render only for HubOwner-at-fleet-scope, SysAdmin, or SuperAdmin; never as disabled controls | FLC-2 | Not run | - |
| FLC-3 | Renaming a fleet changes the displayed label only — enrollment id, grant scopes, log file names, and event records are unaffected | FLC-3 | Not run | - |
| FLC-4 | The VF table lists every VF in the fleet with orca, connection, user, and P95 figures; the access column names the strongest held grant, including grants inherited from the fleet | FLC-4 | Not run | - |
| FLC-5 | Switch sets the working context across header, tree, and all downstream screens in one action; the current VF has no Switch | FLC-5 | Not run | - |
| FLC-6 | The fleet log tails `<fleet-id>.fleet.out` with every VF's orcas merged by time, each line prefixed `<vf>/<job>`, filterable by the five standard filters, and openable in the floating overlay | FLC-6 | Not run | - |
| FLC-7 | Copy and Download emit the filtered view, not the raw buffer | FLC-7 | Not run | - |
| FLC-8 | The fleet timeline splits VFs triage-first with deterministic ordering; every condition chip deep-links to the offending connection or orca | FLC-8 | Not run | - |
| FLC-9 | Fleet Admin's Permissions tab cannot grant repository-scope permissions (FleetViewer, SysAdmin) | FLC-9 | Not run | - |
| FLC-10 | Creating a virtual fleet validates name uniqueness across the hub server, adds the VF to the table and tree, writes an ENROLL event to the fleet log, and lands the user in the new VF's empty state | FLC-10 | Not run | - |

### Virtual Fleet Console (fleet/virtual-fleet/virtual-fleet-ui.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| VFC-1 | The console renders per grant tier; ReadOnly and ReadExec never see mutating actions as disabled controls | VFC-1 | Not run | - |
| VFC-2 | Four KPI tiles compute over this VF only, and their values match the fleet timeline's figures for the same VF | VFC-2 | Not run | - |
| VFC-3 | Stream status is derived from capture and apply job state; a stopped capture reads Error regardless of apply state | VFC-3 | Not run | - |
| VFC-4 | Suspended streams report zero rows and no latency, and are excluded from Attention and triage | VFC-4 | Not run | - |
| VFC-5 | The New stream wizard validates identity, source/target eligibility, table selection, and mode; the resulting stream is inert until activated | VFC-5 | Not run | - |
| VFC-6 | Activation shows a computed plan before any change is applied; re-activation of an unchanged definition reports no change | VFC-6 | Not run | - |
| VFC-7 | All five capture-start options behave as specified; recovery rewind is blocked until the integrate sequence is fetched; state-table recreation is warned in red | VFC-7 | Not run | - |
| VFC-8 | Chained refresh loads as-of the recorded capture position, verified by a clean compare with zero duplicates | VFC-8 | Not run | - |
| VFC-9 | The VF log tails `<vf>.vf.out` with every stream merged by time, job-prefixed, filterable by the five standard filters, and openable in the overlay | VFC-9 | Not run | - |
| VFC-10 | Copy and Download emit the filtered view, not the raw buffer | VFC-10 | Not run | - |
| VFC-11 | A running compare survives closing its window, continues in the background with a Jobs entry, and restores on reopen | VFC-11 | Not run | - |
| VFC-12 | Compare reports IDENTICAL, DIFFERENT with counts, or INCONCLUSIVE when rows were in motion — never a false green | VFC-12 | Not run | - |
| VFC-13 | The VF timeline's CONCERNS, JOBS, and CHECKS bands order deterministically against wobble-free values | VFC-13 | Not run | - |
| VFC-14 | VF Admin's Permissions tab cannot grant fleet or repository scope | VFC-14 | Not run | - |
| VFC-15 | Freeze suspends the scheduler and holds capture positions; no state is dropped without an explicit teardown | VFC-15 | Not run | - |
| VFC-16 | Every lifecycle transition writes an attributed, versioned record to the VF log and the event ledger | VFC-16 | Not run | - |

### Jobs Console (fleet/virtual-fleet/jobs-ui.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| JBS-1 | A finished job appears in Events carrying the same id, with no state disagreement between the two screens | JBS-1 | Not run | - |
| JBS-2 | Every activated, non-suspended stream is reconciled against an expected capture job and apply job; an owed-but-absent job renders as MISSING, sorted to the top, naming its expected connection | JBS-2 | Not run | - |
| JBS-3 | A RETRY job displays attempt number, maximum, time to next attempt, and total failing duration | JBS-3 | Not run | - |
| JBS-4 | A WAITING job displays its wait reason and, when queued, its position | JBS-4 | Not run | - |
| JBS-5 | A RUNNING cyclic job displays uptime and cycle count; one making no progress displays the stalled duration and a HANGING badge | JBS-5 | Not run | - |
| JBS-6 | An acyclic job in progress displays a completion bar with done/total units and percent | JBS-6 | Not run | - |
| JBS-7 | Selection works identically on seeded, derived, and event-driven rows | JBS-7 | Not run | - |
| JBS-8 | The bulk bar names the affected streams and the count of non-controllable rows before any action runs | JBS-8 | Not run | - |
| JBS-9 | Bulk suspend is graceful per job and writes one ledger event naming every job and stream affected | JBS-9 | Not run | - |
| JBS-10 | Suspend holds the checkpoint; resume redoes at most one cycle. Disable refuses an ordinary resume until explicitly re-enabled | JBS-10 | Not run | - |
| JBS-11 | Event-driven rows offer Open event / Open window, never Suspend | JBS-11 | Not run | - |
| JBS-12 | Every row links to the timeline at its own timestamp, at stream, VF, fleet, and global scope | JBS-12 | Not run | - |
| JBS-13 | Jobs scope follows the one VF scope rule — counts shown at a higher level match the screen's contents | JBS-13 | Not run | - |

### Events Console (fleet/virtual-fleet/events-ui.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| EVU-1 | The header states what is and is not an event; no read-only action or automated job cycle produces a row | EVU-1 | Not run | - |
| EVU-2 | An in-flight compare or refresh appears as a single CURRENT event, not as a separate job-shaped duplicate; its id matches the Jobs row holding it | EVU-2 | Not run | - |
| EVU-3 | All six filters compose with AND, and the matching count is visible at all times | EVU-3 | Not run | - |
| EVU-4 | Scope filters offer named objects from the current VF; free-text search is separate | EVU-4 | Not run | - |
| EVU-5 | Default sort is Event ID descending with the indicator visible on load; id order and time order are identical by construction | EVU-5 | Not run | - |
| EVU-6 | Column visibility persists per user; filter selections are session-only | EVU-6 | Not run | - |
| EVU-7 | Expanding a row reveals the field strip and the parameter block in platform terms, not a restated summary | EVU-7 | Not run | - |
| EVU-8 | Every CURRENT event states `clears when` | EVU-8 | Not run | - |
| EVU-9 | Every event with an artifact links to it; View log opens the job log positioned at the event's timestamp | EVU-9 | Not run | - |
| EVU-10 | Arriving from a Job, history row, or timeline marker scrolls to that event and expands it | EVU-10 | Not run | - |
| EVU-11 | Artifact type is a filter, including "has no artifact" *(planned feature)* | EVU-11 | Gated | - |
| EVU-12 | Retention window, edge behavior, oldest held record, and owner are stated on the screen *(planned feature)* | EVU-12 | Gated | - |
| EVU-13 | A filtered range exports as JSONL + signed manifest with artifact digests, and the export is itself recorded as an EXPORT event naming its filter *(planned feature)* | EVU-13 | Gated | - |
| EVU-14 | ACTIVATE and DEFINITION CHANGE events open the versioned before/after diff — the same artifact the plan showed *(planned feature)* | EVU-14 | Gated | - |

### Stream Console (fleet/virtual-fleet/streams/stream-ui.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| STU-1 | Opening a stream opens and activates its log tab; the tab persists across navigation | STU-1 | Not run | - |
| STU-2 | The three-stage strip always renders capture → file log → apply, each naming its connection and current position; a broken stage carries the error text | STU-2 | Not run | - |
| STU-3 | The latency panel links to the stream timeline; the Recent events strip shares ids and attribution with the ledger | STU-3 | Not run | - |
| STU-4 | The Tables section shows last refresh and last compare **per table**; the volume unit is a per-user preference shared with the Tables page | STU-4 | Not run | - |
| STU-5 | Removing a table stops it at the next checkpoint, asks whether in-flight changes drain or are discarded, and leaves other tables running | STU-5 | Not run | - |
| STU-6 | Add table from the Tables toolbar targets the stream filter's stream; with *All streams*, the selected stream | STU-6 | Not run | - |
| STU-7 | The catalogue never lists a table already registered in this stream; a duplicated stream keeps its own list | STU-7 | Not run | - |
| STU-8 | Search filters by identity and physical name; Select all selects only the filtered rows | STU-8 | Not run | - |
| STU-9 | No-key and no-supplemental-logging tables are flagged in the picker, again in review, and named in the event's `flagged` field — but remain registrable | STU-9 | Not run | - |
| STU-10 | Review is mandatory: the primary action in step 1 is Review, never Register; Remove in review unpicks, Back preserves remaining selections; register with zero tables is impossible | STU-10 | Not run | - |
| STU-11 | Registered rows appear as Queued / refresh PENDING / compare NONE / volume `—`; a DEFINITION CHANGE event and toast state the checkpoint and refresh-required semantics | STU-11 | Not run | - |
| STU-12 | No data moves at registration; target objects appear only on the first refresh; registrations persist across reloads; Cancel at any step registers nothing | STU-12 | Not run | - |
| STU-13 | Duplicate defaults to an unused `<source>-copy` name, fixes the virtual fleet, lists only that fleet's target connections, and defaults schedules off | STU-13 | Not run | - |
| STU-14 | A duplicate shares the source capture connection but has its own log position, file log, jobs, checkpoints, and statistics; the original is unaffected | STU-14 | Not run | - |
| STU-15 | A suspended duplicate reports `—` latency, zero rows, 0 MB file log, and idle apply; resume turns all of it on | STU-15 | Not run | - |
| STU-16 | Duplicate metrics and table registrations are derived each render, resolving a chain of duplicates back to the original | STU-16 | Not run | - |
| STU-17 | Suspend holds capture positions; deactivate defaults to retention-first; retire leaves zero files after GC with the definition read-only | STU-17 | Not run | - |
| STU-18 | Destructive teardown requires typing the stream name | STU-18 | Not run | - |

### Operational Timelines (fleet/virtual-fleet/timeline.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| TML-01 | Stream timeline reachable from stream detail (button + latency-tile link) and the sidebar; VF timeline from the VF header, the sidebar, the fleet timeline's VF cards, and `timeline →` links in Jobs and Events | TML-01 | Not run | - |
| TML-02 | Range selector offers 1h / 6h / 24h / 7d; incident onsets hold their absolute time across range changes | TML-02 | Not run | - |
| TML-03 | Stream scope renders four bands (throughput, capture lag, checkpoint lag, backlog); VF scope renders three (total throughput, worst capture lag, total backlog) | TML-03 | Not run | - |
| TML-04 | VF-scope capture lag is the worst stream at every point, never an average; throughput and backlog are sums | TML-04 | Not run | - |
| TML-05 | Ledger events and derived incidents in the window appear as markers on every band and as chips in one lane; clicking a chip moves the cursor to that time and all readouts update together | TML-05 | Not run | - |
| TML-06 | Markers are capped and time-sorted; an empty window states so explicitly | TML-06 | Not run | - |
| TML-07 | Cursor readout reports each band's value at the cursor and names the dominant latency factor | TML-07 | Not run | - |
| TML-08 | Diagnosis strip is computed, not static: stream scope states latency, dominant cause, onset, and projected clear time; VF scope states the counts and names the worst stream and the band it drives | TML-08 | Not run | - |
| TML-09 | Entering the timeline from a Job or Event positions the cursor at that record's timestamp rather than at "now" | TML-09 | Not run | - |
| TML-10 | Infrastructure cards cover hub, repo database, and every distinct source and target agent, deduplicated, showing CPU %+cores, memory %+GB, IO write and read MB/s | TML-10 | Not run | - |
| TML-11 | An unreachable agent's card shows last-seen and no stale stats; an agentless target's card says the hub applies directly | TML-11 | Not run | - |
| TML-12 | Per-stream table shows status, latency, backlog now, rows/min **at cursor**, and a throughput sparkline; clicking a row opens that stream's timeline with cursor position preserved | TML-12 | Not run | - |
| TML-13 | Per-table flow rows show health, peak window (outlined on the 24h strip), and share of stream volume; table name opens table detail | TML-13 | Not run | - |
| TML-14 | Deactivate and Activate cards are both always present, correctly tagged available / no-op / blocked, with projected numbers; the action button invokes the same suspend/resume path used elsewhere and lands in the ledger | TML-14 | Not run | - |
| TML-15 | Fleet scope renders VF cards split triage-first with CONCERNS / JOBS / CHECKS counts and deep-linking condition chips — not combined charts | TML-15 | Not run | - |

### Fleet Paths (Documents/fleet-paths.md)

| ID | Acceptance criterion | Procedure | State | Evidence |
|---|---|---|---|---|
| HPT-01 | Every file a fleet writes resolves to a documented path under the state root, and its console object is derivable from that path alone | HPT-01 | Not run | - |
| HPT-02 | No path segment or file name anywhere contains a display alias; renaming a fleet, VF, or stream leaves the filesystem byte-identical and writes one DEFINITION CHANGE event | HPT-02 | Not run | - |
| HPT-03 | Jobs, Events, VF Timeline, and Fleet Alerts create no directories of their own; their run logs and artifacts appear under the owning stream or the VF's `reports/` and `plans/` | HPT-03 | Not run | - |
| HPT-04 | The stream, VF, and fleet log files exist at their documented paths, each a strict superset of the level below, verified line-for-line after a mixed workload | HPT-04 | Not run | - |
| HPT-05 | No fleet writes a `global.out`; the Global Fleet console's download is generated at read time from reachable fleets and is correct under a partial-reachability fixture | HPT-05 | Not run | - |
| HPT-06 | File-store quota, unacknowledged bytes, and forecast-to-quota are computed per `vf/<vf-id>/` subtree; a VF at quota does not impede its siblings | HPT-06 | Not run | - |
| HPT-07 | Deleting a VF or retiring a stream removes exactly its subtree, leaves no orphans elsewhere, and never overrides `filelog/` acknowledgment-based GC | HPT-07 | Not run | - |
| HPT-08 | Exports, snapshots, downloaded logs, and forwarded events all carry explicit fleet and VF ids; two fleets' artifacts unpack side by side without collision | HPT-08 | Not run | - |
