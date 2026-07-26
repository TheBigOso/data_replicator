# Scheduler and Refresh Modes — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design locked

---

## 1. Purpose and Positioning

The scheduler is the hub component that owns every job's lifecycle — capture, integrate, refresh, and compare — across all logical hubs (one scheduler instance per logical hub). HVR's scheduler design is fundamentally sound and its shape is kept; what this platform adds is the elevation of *scheduled full refresh* from buried plumbing to a first-class pipeline mode, plus the operational controls (calendars, overlap policy) that HVR makes users fight for.

## 2. Pipeline Modes

Chosen at pipeline creation, changeable later; same UI, same pipeline concept, one selector:

**Mode 1 — Continuous CDC.** Log-based capture and continuous/burst integrate; the platform's core.

**Mode 2 — Scheduled refresh.** No log capture at all. On a schedule, the source tables are snapshot and fully reloaded to the target (the "SELECT * on a timer" the market keeps asking for). This mode requires only a SELECT-capable account, which matters twice: it covers sources where log access is unobtainable (unwilling DBAs, third-party application vendors, read replicas), and it gives every engagement a soft start — deploy in an afternoon with read-only privileges, upgrade pipelines to CDC as access and trust mature. Any database reachable by SELECT becomes a valid source location in this mode, expanding the source universe far beyond the log-based connector list.

**Mode 3 — CDC plus scheduled compare.** Continuous replication with a compare job on a cadence (nightly, weekly) proving source-equals-target and alerting on drift. Falls out of the same scheduler for free and turns audit-readiness into a checkbox.

## 3. Job Model and States (HVR parity)

A job performs one task: capture, integrate, refresh, or compare. Jobs are cyclic (rerun repeatedly — capture/integrate, recurring refreshes) or acyclic (run once — an ad-hoc refresh). The state machine is kept from HVR because it is right: PENDING → RUNNING → PENDING (cyclic) or gone (acyclic); on failure, ALERTING → RETRY → run again; a job running beyond its expected envelope is marked HANGING. All states are visible per job in the UI and the REST API, with transitions logged as events.

## 4. Scheduling Controls

**Cron with timezones.** Recurring jobs are scheduled by cron expression evaluated in an explicit named timezone (DST-correct), with human-readable presets ("every night at 2:00 AM Pacific," "hourly on weekdays") so nobody has to hand-roll cron. The schedule editor shows a next-five-runs preview so a misread expression is caught before deployment, not at 3 AM.

**Blackout calendars.** Named maintenance windows during which no scheduled jobs launch, attachable per hub or per pipeline. Patch weekends, quarter-close freezes, and change-moratorium periods are configuration, not a fight with the scheduler. Jobs already running when a blackout begins follow a per-calendar policy: run to completion (default) or checkpoint-and-pause.

**Overlap policy.** If a trigger fires while the previous run is still executing, the behavior is explicit per pipeline — skip (default), queue one, or kill-and-restart. Never ambiguous, never accidental double-runs.

**Retry policy.** Exponential backoff with a configurable ceiling and a hard failure threshold that trips an alert and stops retrying. Slice-level retries (see the Slicing specification) nest inside job-level policy.

## 5. Refresh Mechanics

A naive scheduled `SELECT *` reload has two classic failure modes; both are designed out:

**Consistent snapshot.** All tables in a refresh (and all slices of each table) read as-of a single SCN/LSN where the source supports it, so the reloaded data set is transactionally coherent rather than a smear across the load window. Sources without snapshot support get the documented weaker guarantee, stated per class in the capability matrix.

**Stage-and-swap.** Refresh data lands in staging tables on the target; the swap to live tables is atomic and occurs only when the entire refresh (every table, every slice) has completed. Target readers never observe an empty, partial, or half-loaded table; a failed refresh leaves the previous data untouched and visible.

**Slicing.** Large-table refreshes divide into parallel slices per the Slicing specification — strategy selection, per-slice checkpointing and retry, and the slice map all apply to scheduled refreshes exactly as to activation refreshes.

**One transport.** Refresh data flows through the same file log, hub relay, compression/encryption, and bulk-apply path as CDC bursts. One pipeline concept, one transport, two capture modes — no parallel machinery to build, test, or explain.

## 6. HVR Parity Matrix

| HVR scheduler concept | This platform | Delta |
|---|---|---|
| Scheduler per logical hub | Same | Kept |
| Job types: capture/integrate/refresh/compare | Same | Kept |
| Cyclic and acyclic jobs | Same | Kept |
| States: PENDING/RUNNING/ALERTING/RETRY/HANGING | Same machine | Kept, fully surfaced in API |
| Recurring refresh via job attributes | Scheduled refresh as a pipeline mode | First-class, UI-native |
| — | Cron + timezone + presets + next-run preview | New |
| — | Blackout calendars | New |
| — | Explicit overlap policy | New |
| — | CDC + scheduled compare mode | New (drift-proof automation) |
| Refresh consistency left to operator | Snapshot-consistent, stage-and-swap by default | Designed-out failure modes |

## 7. Test Plan

Phased plan; the standing rule applies (procedure executed, results observed, evidence archived — no procedure, no pass), and the full suite reruns as regression on every merge touching this area.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Timing determinism | SCH-01, SCH-02, SCH-03, SCH-04, SCH-05, SCH-10, SCH-11 | Virtual clock + job stubs | Scheduler consumes injectable time | Simulated-year and policy matrices exact |
| B | Refresh mechanics and modes | SCH-06, SCH-07, SCH-08, SCH-09 | Integration lab under TPC-C | Phase A exit; refresh engine implemented | Snapshot, swap, SELECT-only, and drift behaviors proven under load |

### 7.1 Methods

The scheduler's defining test asset is a **virtual clock**: the scheduler consumes time through an injectable source, so a 30-day calendar simulation — DST transitions, blackout edges, trigger-aligned boundaries — runs in seconds and deterministically (SCH-01, SCH-02, SCH-11). Wall-clock scheduler tests are flaky by nature; virtual time makes every timing criterion exact and repeatable.

**Policy tests** use controllable job stubs: a deliberately slow refresh under a fast trigger exercises all three overlap policies (SCH-04); an injectable failure sequence verifies the retry curve and the single-alert threshold (SCH-05); a stall stub proves HANGING detection latency (SCH-10); blackout-onset behavior is tested for both per-calendar policies (SCH-03).

**Refresh mechanics** run in the integration tier against live load: snapshot consistency is verified by running the refresh under concurrent TPC-C updates and auditing cross-table foreign-key coherence in the result (SCH-07); stage-and-swap is verified by a reader process polling the live tables continuously through refreshes and through a deliberately killed refresh, asserting it never observes a missing or partial table (SCH-08). **Mode tests** cover the SELECT-only account path with compare verification each cycle (SCH-06) and seeded target drift caught by the scheduled compare within one cycle (SCH-09).

## 8. Test Procedures

Timing procedures (SCH-01 through SCH-05, SCH-10, SCH-11) run on the virtual clock unless stated; refresh procedures run in the integration lab under live load.

### SCH-01 — Cron correctness across DST
**Steps:** (1) Configure schedules in America/Los_Angeles and Europe/Berlin (daily 02:30, hourly, weekday-only fixtures). (2) Advance the virtual clock across both DST transitions for each zone over a simulated year. (3) Diff actual fire times against an independently computed expected set.
**Expected:** Exact match, including the spring-forward nonexistent-time and fall-back ambiguous-time policies as documented.
**Evidence:** Fire-time diff (empty), policy-case log.

### SCH-02 — Blackout calendars honored
**Steps:** (1) Attach hub-level and pipeline-level calendars including windows edge-aligned to trigger times. (2) Simulate 30 days with dense triggers. (3) Assert zero launches inside any window; assert the first post-window trigger fires.
**Expected:** Zero in-window launches over the full simulation; boundary triggers behave per the documented inclusive/exclusive rule.
**Evidence:** Launch log vs calendar overlay.

### SCH-03 — Blackout onset mid-run
**Steps:** For each policy: (1) Start a controllable long-running refresh stub. (2) Trigger blackout onset mid-run. (3) Observe: run-to-completion finishes; checkpoint-and-pause checkpoints, pauses, and resumes at window end.
**Expected:** Each policy behaves exactly as configured; the paused run resumes from checkpoint with no rework (stub verifies offset).
**Evidence:** Stub state timeline per policy.

### SCH-04 — Overlap policies
**Steps:** Slow stub (runtime 3× trigger interval), one run per policy over 10 triggers: skip, queue-one, kill-and-restart.
**Expected:** Skip: exactly the runs that started with no overlap, skips logged. Queue-one: never more than one queued; queue collapses, doesn't grow. Kill-and-restart: prior run terminated cleanly (stub confirms checkpoint), new run starts; no orphan processes.
**Evidence:** Run/skip/queue/kill tallies per policy vs expected.

### SCH-05 — Retry curve and threshold
**Steps:** (1) Configure backoff (base, multiplier, ceiling) and threshold 5. (2) Stub fails deterministically. (3) Record retry timestamps; verify curve. (4) Confirm exactly one alert at threshold and no further retries. (5) Clear the fault; manually resume.
**Expected:** Intervals match the configured curve within tolerance; single alert; halt is durable until operator action.
**Evidence:** Retry timeline, alert record.

### SCH-06 — Mode 2 with SELECT-only account
**Steps:** (1) Pipeline in scheduled-refresh mode against the SELECT-only lab location, nightly virtual schedule. (2) Run three cycles with data mutations between cycles. (3) Compare after each cycle.
**Expected:** Three clean compares; source session audit shows SELECT-class statements only.
**Evidence:** Compare reports, session audit.

### SCH-07 — Snapshot consistency under load
**Steps:** (1) Start TPC-C at full rate on the lab source. (2) Run a multi-table sliced refresh with snapshot consistency. (3) On the target result, audit cross-table FK coherence (orders ↔ order-lines counts as-of the snapshot) and verify no row postdates the snapshot SCN.
**Expected:** Zero FK orphans; zero post-snapshot rows; the snapshot SCN recorded in the run metadata matches the data.
**Evidence:** FK audit output, SCN boundary check.

### SCH-08 — Stage-and-swap invisibility
**Steps:** (1) Reader process polls the live target tables at 100ms intervals throughout. (2) Run a full refresh to completion. (3) Run a second refresh and kill it at 60%. (4) Reader log analysis.
**Expected:** Reader never observes a missing table, empty table, or row count outside {old, new} complete states; after the killed refresh, live tables still hold the prior complete data.
**Evidence:** Reader observation log, post-kill table state.

### SCH-09 — Drift detection (Mode 3)
**Steps:** (1) CDC pipeline with nightly scheduled compare (virtual clock). (2) Manually mutate 50 target rows across 3 tables. (3) Advance to the next compare cycle.
**Expected:** Compare detects exactly the seeded differences and raises the drift alert within one cycle; report identifies tables and difference counts.
**Evidence:** Compare report vs seed list, alert record.

### SCH-10 — State visibility and HANGING detection
**Steps:** (1) Poll the REST API jobs endpoint at 1s during a scripted sequence: normal cycle, induced failure/retry, and a stall stub exceeding its envelope. (2) Record observed states.
**Expected:** Every documented transition (PENDING/RUNNING/ALERTING/RETRY) observed within one poll interval of occurrence; stall marked HANGING within the configured envelope.
**Evidence:** API state timeline vs scripted ground truth.

### SCH-11 — Next-run preview accuracy
**Steps:** (1) For 20 fixture schedules (mixed zones, calendars attached), capture the editor's next-five-runs preview. (2) Simulate the following week on the virtual clock. (3) Diff actual fires against previews.
**Expected:** Exact match for all fixtures, including calendar-suppressed runs shown as suppressed in the preview.
**Evidence:** Preview-vs-actual diff (empty).

## 9. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| SCH-01 | Cron schedule in a DST-observing timezone fires correctly across both DST transitions (simulated clock) |
| SCH-02 | No job launches inside an active blackout window over a 30-day simulated calendar including edge-aligned triggers |
| SCH-03 | Blackout beginning mid-run: run-to-completion and checkpoint-and-pause policies each behave as configured |
| SCH-04 | Overlap policies: a deliberately slow refresh under a fast trigger produces exactly the configured behavior for skip, queue-one, and kill-and-restart |
| SCH-05 | Retry backoff follows the configured curve; the failure threshold trips exactly one alert and halts retries |
| SCH-06 | Mode 2 pipeline with a SELECT-only account completes recurring reloads; compare verifies each against source |
| SCH-07 | Snapshot consistency: refresh under concurrent TPC-C updates yields a target coherent as-of one SCN (cross-table FK audit) |
| SCH-08 | Stage-and-swap: target readers polling throughout a refresh never observe a missing or partial table; a killed refresh leaves prior data intact |
| SCH-09 | Mode 3: seeded drift (manual target mutation) is detected by the scheduled compare and alerts within one cycle |
| SCH-10 | Job state transitions (including HANGING detection on a stalled job) are visible via REST API within one poll interval |
| SCH-11 | Schedule editor next-run preview matches actual fire times over a week-long simulation |

## 10. Open Questions

Default HANGING thresholds per job type need benchmark-derived envelopes rather than fixed guesses. Whether Mode 2 supports incremental keyed reloads (high-watermark column) as a sub-mode — useful but scope-adjacent to CDC — is deferred to a v1.x decision. Calendar import (iCal) for enterprise change calendars is a candidate convenience feature awaiting demand.
