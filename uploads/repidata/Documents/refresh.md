# Refresh — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design; one refresh engine serving three roles

---

## 1. Purpose and Positioning

Refresh is the bulk movement of table data from source to target — reading rows (not logs) and loading them. One engine serves three roles, deliberately: the **initial load** chained from stream activation (stream spec 6.4–6.5), the **scheduled reload** that is stream Mode 2 (scheduler spec), and the **repair tool** that puts a damaged or drifted target right without rebuilding the stream. HVR ships the same trinity under `hvrrefresh`; our departure is that the mechanics — snapshot consistency, staging, the online handshake — are explained to the operator rather than performed behind a dialog.

**UI entry point:** the stream's primary action is **Activate replication** (plan-based, stream spec §6), and refresh rides that plan as the chained initial load — activation first establishes the capture position, then the refresh reads as-of that same snapshot, so capture and load meet with no gap. On an already-active stream the same dialog is a verify plan whose chained reload serves the repair role; there is no standalone refresh button.

## 2. The Two Refresh Methods

### 2.1 Bulk refresh — fastest path to a correct target

Bulk refresh replaces the target's contents: read the source table (sliced if large), ship rows through the same file-log transport as CDC (compressed, encrypted, sequenced — refresh data is never a special case with weaker guarantees), and load the target through its fastest ingestion path — a native bulk interface where the target has one, or staged files where it doesn't (the staging location and its cleanup are documented per target class in the capability matrix; nothing to discover).

The load lands in **staging tables, never live ones**, and the swap to live is atomic and whole-refresh-or-nothing — the stage-and-swap discipline specified in the scheduler document (SCH-08): readers never see an empty or partial table, and a failed refresh leaves yesterday's complete data untouched. Where a target's bulk path benefits from it, indexes and constraints on staging are created after loading, not before.

### 2.2 Row-wise refresh — minimal disturbance

Row-wise refresh makes the target match the source by applying only the differences: it runs the compare machinery (compare spec) to find missing, extra, and changed rows, then applies precisely those inserts, deletes, and updates. Rows already in sync are never rewritten — which preserves target-side history mechanisms, avoids blowing away downstream incremental loads, and turns a 500-million-row table with 4,000 drifted rows into a 4,000-write repair instead of a full reload. Row-wise is the natural repair tool; bulk is the natural first load. One cost profile deserves stating: on column-oriented targets (Snowflake, Databricks, Redshift-class), row-wise repair executes per-row DML that columnar engines handle poorly — right for small drift counts, wrong for large ones, with the crossover documented per target class in the capability matrix. The UI recommends accordingly and says why, including this columnar caveat.

Row-wise repair also accepts **repair class filters** (HVR's 6.2.5 addition, kept): skip inserts (keys existing only in source), skip deletes (keys existing only in target), or skip updates — for repairs where one difference class is intentional, such as a target deliberately retaining rows the source has deleted. Excluded classes are omitted from the applied fix set and from the generated difference output alike, and the run record names the active filters — a repair's verdict is meaningless without knowing what it was told to ignore (the compare spec's relaxation rule, applied to repair).

### 2.3 Additive merge refresh — the honest upsert

A third mode for a narrow job: merge source rows into the target **without deleting or truncating anything**. Rows load through the burst staging path and merge as inserts and updates only — HVR's upsert refresh, kept, available only on burst-capable targets and never for TimeKey tables (append-only semantics make "upsert" meaningless there). Its non-convergence is stated where the mode is chosen, not discovered from drift: source-side deletes remain on the target, and a source key-update leaves both the old and new key present. Because an additive merge deliberately leaves the target a superset, the run record flags the mode and the sync report annotates subsequent extra-row differences on affected tables with the merge-refresh provenance — the report explains the drift this mode causes instead of crying wolf about it.

## 3. Consistency — the snapshot guarantee

All tables in a refresh, and all slices of every table, read **as-of one source position** (SCN/LSN) where the source supports consistent reads: the loaded data set is transactionally coherent — order 1042's header and its lines agree — rather than a smear across the read window. Sources without snapshot capability get the documented weaker guarantee, stated per class in the capability matrix, never silently. The snapshot position is recorded in the refresh run's metadata and shown in the UI, because that position is the answer to "as of when is this data?" — a question auditors ask.

## 4. The Online Handshake — refresh under live changes

Refreshing a table that applications are actively changing is the hard case, and the mechanism deserves its plain-language explanation (it is step 8 of the activation walkthrough, generalized):

1. The refresh records the source position **S** at its snapshot instant and reads everything as-of S.
2. Capture (running or starting) owns every change committed **after** S.
3. Integrate knows each table's **refresh boundary**: captured changes at or before S for a refreshed table are skipped — the refresh already delivered that state; changes after S apply normally.

No quiesce, no gap, no overlap — and no "double apply" corruption where a change lands both in the snapshot and as a captured event. The boundary bookkeeping is per table, so a refresh of three tables in a fifty-table stream coordinates only those three. This is what HVR calls online refresh; here the boundary values are visible in the run record, so an operator can verify the handshake rather than trust it.

**Coordination with integrate — no suspension, no control files.** HVR's default coordination is blunt: starting a refresh forces the integrate job into SUSPEND and writes block control files on the hub; when a refresh fails, those files can be left behind and integrate cannot restart until an operator finds and deletes them by name from `HVR_CONFIG` — a documented sharp edge. This platform has no equivalent state to leak, because the handshake *is* the coordination: integrate keeps running throughout every refresh, applying captured changes to every table and skipping only what falls at-or-before a refreshed table's boundary. HVR's optional "isolated refresh" (integrate continues for tables outside the refresh) is therefore not an option here — per-table boundaries make it the only behavior. A refresh that dies mid-run simply never installs its boundaries: integrate was never blocked, nothing needs cleanup, and the rerun starts clean (REF-09 proves all of this under load). Refresh-vs-refresh concurrency on the same stream is governed by the scheduler's explicit overlap policy, not by hidden files.

**Skip policy and broadcast safety.** *Where* do pre-refresh changes get skipped? Our default is HVR's write-side option made structural: boundaries live in each target's integrate bookkeeping, so refreshing one broadcast target never affects what the others receive. The capture-side variant — skip pre-boundary changes at the source, saving network and parser work — exists as an optimization, but the planner gates it: requesting capture-side skip on a stream with other consumers of those changes produces a warning naming the targets that would then need their own refresh. HVR documents this hazard as a paragraph of advice; here it is a computed check. The no-skip resilient variant is kept for context-restricted refreshes (a predicate-scoped reload where pre-refresh changes must still apply normally and only the refresh window's changes need resilient handling).

## 5. Scope, Slicing, and Scheduling

A refresh names its scope: whole stream, table subset, or a **filtered subset** of rows (a predicate per table — the repair scenario "reload March for the orders table" is a first-class parameter, not a workaround). Large tables slice per the Slicing specification — strategy selection, per-slice checkpoint and retry, the slice map, and the Advisor all apply identically to refreshes invoked from activation, from a schedule, or ad-hoc. Scheduling-wise a refresh is a job like any other: recurring (Mode 2, cyclic) or ad-hoc (acyclic, run-once), under the scheduler's calendars, overlap policies, and state machine.

## 6. Load-Time Target Mechanics

**Foreign keys.** A bulk reload of tables enmeshed in foreign-key constraints needs them out of the way: the refresh plan can disable referencing and referenced constraints before the load and re-enable them after (drop-and-recreate where the DBMS lacks disable syntax), capability-gated per target class and shown as explicit plan steps. The online-refresh nuance is kept and stated plainly: with live changes in flight, re-enablement defers to the end of the next integrate cycle — the moment the target is consistent again — and the run record shows the deferral. Left unhandled, FK errors are the expected outcome; the plan says so up front instead of letting the operator find out.

**Triggers.** Target-side triggers firing on refresh writes are usually unwanted double-processing. Suppression during the load is a capability-gated setting with per-DBMS mechanics documented rather than discovered: session-level suppression where the DBMS offers it, and SQL Server's not-for-replication connection path with its connection-string form and encryption caveats stated in the capability matrix.

**The TimeKey truncate marker.** A bulk refresh into a TimeKey file or Kafka target can prepend a **truncate marker record** as each table's first record (HVR's option, kept): a published-format signal telling downstream consumers that every prior record for the table is superseded by this reload. Without it, an append-only audit stream has no way to say "start over"; with it, the semantics are explicit and machine-readable — the marker is part of the published TimeKey metadata specification, not a magic row.

## 7. Target Table Creation

Refresh can create or reconcile target tables per the creation-policy set specified in the stream document (6.4): create-missing, create-and-alter-mismatched, recreate-all, with keep-existing-structure, keep-old-rows, and no-index modifiers. One policy engine, referenced here rather than restated — behavior and its tests (STR-18) are owned by the stream spec; this document owns the data-movement behaviors.

## 8. HVR Parity Matrix

| HVR refresh concept | This platform | Delta |
|---|---|---|
| hvrrefresh: initial load, scheduled, repair | One engine, three roles | Kept |
| Bulk refresh (truncate + bulk load, -gb) | Bulk into staging + atomic swap | Truncate window eliminated; readers never exposed |
| Row-wise refresh | Row-wise via compare + minimal apply | Kept; minimal-write property stated and tested |
| Online refresh (capture coordination) | Online handshake with visible per-table boundaries | Kept; boundaries auditable in the run record |
| Consistent as-of read | Single-position snapshot, recorded and displayed | Kept; position surfaced |
| Slicing (-S) | Full slicing spec applies | Kept, deepened (see Slicing) |
| Table/row scope options | Table subset + per-table predicates | Repair scope is first-class |
| Create-table options (-cb*) | Stream creation-policy engine | Owned by stream spec, one engine |
| Staging for non-bulk targets | Documented per class in capability matrix | Nothing to discover |
| Integrate forced to SUSPEND during refresh via block control files; failed refresh can strand them, requiring manual file deletion | No suspension: integrate runs throughout, coordinated by per-table boundaries; no control-file state exists to strand | Sharp edge removed structurally (REF-09) |
| Isolated refresh as an option (integrate continues for non-refreshed tables) | Per-table boundary bookkeeping — isolation is the only behavior | Default, not option |
| Row-wise on column-oriented targets slow for large diffs (doc note) | Same physics; per-class crossover guidance in the capability matrix and the UI recommendation | Warned where the choice is made |
| Refresh source must be a database location; target database or file | Same rule, enforced from the capability matrix at configuration time | Config-time refusal, not runtime failure |
| Five-day free-refresh window under consumption (MAR) licensing | No metering exists; refresh is never a billable event | Flat license |
| Merge into target / upsert refresh (-u) | Additive merge mode; non-convergence stated at selection and annotated in the sync report | Kept, made honest |
| Idempotent Load option (-k) for BigQuery/Databricks/Snowflake | Stage-then-atomic-swap architecture has no truncate-retry window to protect | Their opt-in fix is our default shape |
| Only Repair Certain Differences (-m) | Repair class filters, named in the run record and excluded from diff output | Kept; relaxations always named |
| FK disable/re-enable (-F), online re-enable deferred to next integrate cycle | Constraint handling as visible, capability-gated plan steps; the deferral recorded | Kept, surfaced |
| Disable triggers (-f), per-DBMS mechanics | Capability-gated suppression; connection-path caveats in the matrix | Kept; caveats stated, not discovered |
| TimeKey truncate record (-n) for file/Kafka | Truncate marker in the published TimeKey metadata specification | Kept; part of the public format |
| Online skip policy -q (read/write, write-only, resilient) | Write-side per-target boundaries structural default; capture-side skip planner-gated on other consumers; resilient kept | Broadcast hazard computed, not documented |
| Scheduling: now / once / repeatedly / delay-suspended | Scheduler-native; delay = the leave-suspended start policy (stream 6.7) | One scheduler, one pattern |
| Refresh task name for naming scripts and jobs | No generated scripts exist; jobs are internally named and queryable | Nothing to name |
| Entry points across seven pages incl. Repeat Refresh from event | Scoped-surface pre-fill and idempotent repeat, same as activation (stream 6.7) | Same pattern everywhere |

## 9. Test Plan

Phased plan; the standing rule applies (procedure executed, results observed, evidence archived — no procedure, no pass); full REF suite reruns on merges touching the refresh engine. Boundary-owned criteria referenced from other specs (SCH-07/08 snapshot and swap under the scheduler, STR-18 creation policies, SLC-* slicing) are not duplicated here; the matrix links them.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Data-movement correctness | REF-01, REF-02, REF-03 | Integration lab, TPC-C | Bulk and transport paths implemented | Bulk, staged-target, and transport-parity proven |
| B | Online and row-wise | REF-04, REF-05, REF-06, REF-09, REF-10, REF-11 | Lab under full concurrent load + broadcast, FK, and trigger fixtures | Phase A exit; compare engine available | Handshake boundary, minimal-write repair, never-suspended coordination, merge/filter/marker modes, and skip/constraint/trigger handling proven |
| C | Scope and lifecycle | REF-07, REF-08 | Lab + scheduler | Phase B exit | Filtered repair and ad-hoc lifecycle proven |

### 9.1 Methods

Movement tests verify the bulk path per target class (native bulk interface and staged-file variants), always ending in compare. Transport-parity tests assert refresh files ride the identical file-log guarantees as CDC (encryption, sequencing, checksums) by inspection of the hub store. Online tests run refreshes under full TPC-C concurrency and audit the boundary: no change lost, none double-applied, verified by compare plus a targeted audit of rows modified within seconds of the snapshot position — the exact population where handshake bugs live. Row-wise tests measure writes: repairing N seeded drift rows must touch O(N) rows, asserted from target statement counts. Scope tests seed drift inside and outside a predicate and assert the repair respects the fence. Coordination tests (REF-09) monitor integrate job state and per-table latency continuously through scoped refreshes — including one killed mid-run — asserting integrate is never suspended and no blocking residue survives a failed refresh.

## 10. Test Procedures

### REF-01 — Bulk refresh correctness and swap atomicity
**Steps:** (1) Bulk-refresh a 20-table stream while a reader polls live tables at 100ms. (2) Compare all tables. (3) Rerun and kill the refresh at 70%; inspect live tables and staging cleanup.
**Expected:** Compare clean; reader never observes missing/partial tables; killed run leaves prior data live and staging cleaned per policy.
**Evidence:** Compare reports, reader log, post-kill audits.

### REF-02 — Staged-target bulk path
**Preconditions:** Lab target without a native bulk interface (per capability matrix).
**Steps:** (1) Bulk-refresh through the staged-file path. (2) Verify staging location use, load, and cleanup per the documented lifecycle. (3) Compare.
**Expected:** Load succeeds via documented staging; zero residue post-run; compare clean.
**Evidence:** Staging audit trail, compare report.

### REF-03 — Transport parity for refresh data
**Steps:** (1) During a refresh, capture its files from the hub store. (2) Verify encryption (payload unreadable without key), sequencing, and checksums identically to CDC files; attempt a tampered-file apply.
**Expected:** Refresh files indistinguishable in guarantees from CDC files; tampered file rejected on authentication.
**Evidence:** File inspection output, rejection log.

### REF-04 — Online handshake under full load
**Steps:** (1) TPC-C at full rate; run an online refresh of 5 hot tables. (2) Record the snapshot position S and per-table boundaries from the run record. (3) After catch-up, compare. (4) Audit rows whose source commits fall within ±5 seconds of S: each must appear exactly once in the final state.
**Expected:** Compare clean; boundary-adjacent audit shows zero lost and zero double-applied changes; boundaries in the run record match observed behavior.
**Evidence:** Run record, compare report, boundary audit.

### REF-05 — Row-wise repair with minimal writes
**Steps:** (1) Seed 4,000 drift rows (mix of missing, extra, changed) across a 10M-row table. (2) Run row-wise refresh with target statement auditing. (3) Re-compare.
**Expected:** Re-compare clean; target writes on the order of the drift count, not the table size (threshold documented); in-sync rows untouched.
**Evidence:** Statement counts vs seed count, compare reports before/after.

### REF-06 — Row-wise vs bulk equivalence
**Steps:** (1) Clone a drifted target. (2) Repair one clone row-wise, reload the other bulk. (3) Compare both against source and against each other.
**Expected:** Both end identical to source (and to each other) — two roads, one truth.
**Evidence:** Three compare reports.

### REF-07 — Filtered-scope repair
**Steps:** (1) Seed drift both inside and outside a date predicate ("March rows") on one table. (2) Run a refresh scoped to that table and predicate. (3) Audit: inside-drift repaired, outside-drift untouched; then full compare to confirm the outside drift is still detectable.
**Expected:** The fence holds exactly; scope shown in the run record.
**Evidence:** Inside/outside audits, run record.

### REF-08 — Ad-hoc refresh lifecycle
**Steps:** (1) Launch an ad-hoc (acyclic) refresh via UI and via CLI. (2) Verify scheduler treatment: PENDING→RUNNING→gone, overlap policy honored against a running cyclic job on the same stream, event trail complete.
**Expected:** Acyclic semantics per the scheduler spec; both invocation paths equivalent (parity rule).
**Evidence:** Job state timeline, event log, CLI transcript.

### REF-09 — Integrate never suspended; no blocking residue
**Preconditions:** 20-table stream under full TPC-C; integrate job state pollable via REST at 1s; per-table latency metrics.
**Steps:** (1) Run an online refresh scoped to 5 tables to completion. (2) Throughout, record the integrate job's state and the latency series of the 15 non-refreshed tables. (3) Compare all 20 tables after catch-up. (4) Rerun the scoped refresh and kill it at ~50%; verify integrate state through and after the kill; audit the hub store and repository for any blocking artifact; rerun the refresh to completion with no manual intervention; compare again.
**Expected:** The integrate job never enters a suspended or blocked state in either run; non-refreshed tables' latency stays flat (within normal variance) throughout; both compares clean; the killed refresh leaves zero blocking residue — the rerun starts and completes untouched by the failure.
**Evidence:** Job-state timeline (1s resolution), latency series, compare reports, post-kill artifact audit.

### REF-10 — Additive merge, repair filters, truncate marker
**Steps:** (1) On a burst-capable target seeded with rows the source has since deleted, plus one source key-update case, run an additive merge refresh; assert inserts and updates applied, source-deleted rows and the old-key row still present (the documented non-convergence), the run record flagging the mode, and the next sync report annotating the extra rows with merge-refresh provenance. (2) On a soft-delete-style fixture, run row-wise repair with the no-deletes filter: deletes skipped, inserts/updates applied, active filters named in the run record and absent from the difference output; rerun unfiltered and assert convergence. (3) Bulk-refresh a TimeKey stream into the lab file target with the truncate marker enabled; assert each table's first record is the marker per the published format and a consumer script honoring it reconstructs exactly the post-refresh state. (4) Assert the merge mode is refused for TimeKey tables and on non-burst-capable targets with capability-matrix messages.
**Expected:** Merge behaves and annotates as documented; filters honored and recorded; marker published-format-exact and consumer-verifiable; refusals correct.
**Evidence:** Target audits, run records, sync report excerpt, marker decode, consumer reconstruction diff (empty), refusal messages.

### REF-11 — Skip policy, constraints, and triggers
**Preconditions:** Broadcast stream (targets A and B) under TPC-C; FK fixture (parent/child tables); trigger fixture (target trigger writing an audit row).
**Steps:** (1) Online-refresh target A only, default write-side policy; assert target B's integrate receives and applies all changes including pre-boundary ones (compare B clean; B's latency flat). (2) Request capture-side skip on the same stream; assert the planner warns naming target B; then on a single-consumer stream, apply capture-side skip and verify via hub-store audit that pre-boundary changes never leave the source. (3) Bulk-refresh the FK fixture with constraint handling enabled: constraints disabled and re-enabled as visible plan steps; repeat as an online refresh and assert re-enablement defers to the next integrate cycle end with the deferral in the run record; repeat unhandled and assert the plan's stated FK-error expectation. (4) Refresh the trigger fixture with suppression: zero trigger side-effects during the load, trigger active immediately after; compare everywhere.
**Expected:** Write-side default is broadcast-safe; capture-side skip is gated and effective; FK and trigger handling behave as visible, capability-gated plan steps with the online deferral recorded.
**Evidence:** Compare reports, planner warning, wire/hub-store audit, plan step captures, deferral record, trigger side-effect audit.

## 11. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| REF-01 | Bulk refresh is compare-clean with atomic swap; readers never observe partial state; a killed run leaves prior data live |
| REF-02 | Targets without native bulk interfaces load via the documented staging lifecycle with zero residue |
| REF-03 | Refresh data carries identical file-log guarantees to CDC (encryption, sequencing, authentication) |
| REF-04 | Online refresh under full load loses nothing and double-applies nothing at the snapshot boundary, with boundaries auditable in the run record |
| REF-05 | Row-wise repair touches O(drift) rows, never O(table); re-compare clean |
| REF-06 | Row-wise and bulk refresh converge a drifted target to identical, source-equal states |
| REF-07 | Filtered-scope refresh repairs exactly inside the predicate fence |
| REF-08 | Ad-hoc refreshes follow acyclic scheduler semantics identically from UI and CLI |
| REF-09 | Integrate is never suspended by a refresh: non-refreshed tables replicate with flat latency throughout a scoped online refresh, and a killed refresh leaves no blocking state — the rerun needs no manual cleanup |
| REF-10 | Additive merge refresh applies inserts/updates only with its non-convergence flagged and sync-report-annotated; repair class filters are honored and recorded; the TimeKey truncate marker is published-format-exact and consumer-verifiable; invalid mode combinations are refused |
| REF-11 | The write-side skip default is broadcast-safe; capture-side skip is planner-gated when other consumers exist; FK and trigger handling are visible, capability-gated plan steps with online re-enable deferral recorded |
| — | Snapshot consistency, stage-and-swap under readers: owned by SCH-07, SCH-08. Creation policies: STR-18. Sliced refresh mechanics: SLC-01..10, SLC-16..17 |

## 12. Open Questions

Row-wise repair ordering under active replication (repair writes interleaving with integrate applies on the same rows) needs a locking/sequencing decision with the compare online design. Whether filtered refresh predicates should be validated against slicing predicates for overlap (a filtered refresh of a sliced table) is a planner question. Default reader-visible swap technique per target class (rename vs partition exchange vs transactional DDL) to be chosen per connector with the documented trade-offs.
