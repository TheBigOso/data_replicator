# Jobs — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design; state machine rationalized from HVR

---

## 1. Purpose and Positioning

A **job** is a process that performs one task: capturing changes, integrating changes, refreshing data, comparing data, applying an activation plan, or producing a sync report. Jobs are the unit the scheduler manages (scheduler spec owns *when* jobs run — cron, calendars, overlap, retry curves; this document owns *what a job is* — its states, its event model, its logs, and its settings). Every job's output lands in a retrievable run log, and failed jobs retry automatically under the scheduler's policy.

Two shapes, kept from HVR because they carve reality correctly: **cyclic** jobs rerun repeatedly — capture and integrate cycle for the life of a stream, a scheduled refresh or compare cycles per its cadence — returning to PENDING after each run to await their next trigger. **Acyclic** jobs run once and finish — an ad-hoc refresh, a one-time compare, an activation. The state machine below serves both; acyclic jobs simply end in a terminal state instead of returning to PENDING.

## 2. Job States — the machine, rationalized

HVR's state list is proven at its core and muddled at its edges: DONE, READY, ERROR, and FAILED overlap enough that "what state is my job in and what does it mean" is a genuine support-ticket category. We keep the core and rationalize the terminals. Every state is visible in the UI and API; every transition is recorded as an event with its cause.

**Scheduling states.** `PENDING` — waiting for its trigger (a cyclic job's resting state). `WAITING` — trigger known and in the future (the next-fire time is shown, per the scheduler's next-run preview). `SUSPENDED` — paused by an operator; resumable, returning to PENDING or RUNNING. Suspension is **graceful by default** — the job completes its current cycle before pausing, with drain progress visible; a **force** option stops immediately and remains checkpoint-safe by construction, costing at most redone work on resume, never correctness (stream spec, section 7.3). `DISABLED` — administratively locked; **not** resumable by an ordinary resume, requiring explicit re-enable (the suspend/disable distinction is kept from HVR exactly because operators need a lock that survives well-meaning colleagues).

**Execution states.** `RUNNING` — in progress, with structured progress where the task supports it (percent, current table/slice, positions). `HANGING` — still RUNNING past its expected envelope (envelope per job type, benchmark-derived — see scheduler open questions); a HANGING job that finishes normally transitions out cleanly, because HANGING is a flag on RUNNING, not a verdict.

**Failure-handling states.** `ALERTING` — the run failed; the alert has fired. `RETRY` — rerunning under the backoff curve. The ALERTING → RETRY → RUNNING loop continues until success or the retry threshold trips (scheduler SCH-05).

**Terminal states — the rationalization.** Exactly two: `SUCCEEDED` and `FAILED`. A FAILED job carries a **cause**: `error` (execution errors exhausted retries), `canceled` (an operator stopped it), or `abandoned` (threshold policy gave up). HVR's DONE / READY / ERROR / FAILED quartet maps onto these two states plus the cause field and the event log — one place to look, no folklore about which terminal means what. Cyclic jobs never reach a terminal state except at stream retirement; acyclic jobs always do.

The full transition diagram is published in the documentation, and JOB-01 tests every edge of it — a transition not in the diagram is a bug by definition.

## 3. Event-Driven Long Tasks

Activate, refresh, compare, and report generation can run for hours; holding an HTTP request open for hours is not an API, it's a timeout. HVR's event pattern is the right answer and is kept whole:

1. The client (UI, CLI, or REST — all the same API) **creates an event**: `POST /streams/{ch}/compare` returns immediately with an **event ID**.
2. The event is recorded in the repository with state ACTIVE and an associated job (created under the scheduler at event creation if it doesn't exist).
3. The job starts, queries for its ACTIVE events, and executes what it finds.
4. The client follows along by polling or streaming the event: **structured progress** (state, percent, current table and slice, positions, ETA from the slice map where applicable), not just "still running."
5. Artifacts attach to the event: an activation's applied plan, a compare's report, a refresh's run record with its snapshot position. When the work finishes, the event carries the terminal state, its cause on failure, and its artifacts — the complete story in one queryable object.

Our additions to HVR's pattern: **cancellation** is first-class (`DELETE` or cancel endpoint on the event → the job stops at the next checkpoint, cleanly, and the event terminates as canceled — sliced work stops at slice boundaries per the slicing spec's checkpoint discipline), and progress is structured rather than log-scraped.

### 3.1 Worked example — the life of a compare event

`POST /hubs/prod/streams/orders/compare` returns `{event_id: 8812, state: ACTIVE, job: orders-cmp}` in milliseconds. The `orders-cmp` job appears PENDING, then RUNNING. `GET /events/8812` at any point returns state, percent, the table currently comparing, and slices completed. Twenty minutes later the event reads `state: FINISHED, result: SUCCEEDED`, with the difference report attached as its artifact — the same report the sync-report stream archives. Had an operator sent the cancel call at minute ten, the job would have checkpointed at the current slice boundary and the event would read `FAILED, cause: canceled`, resumable per the compare spec's checkpoint rules. Nothing here is UI magic: the UI's Jobs page is doing exactly these calls.

## 4. Triggers — what makes a job run

A PENDING job runs when triggered: by the **scheduler** (cron firing, per the scheduler spec's calendars and overlap policies); by **data dependency** (an integrate job is triggered by new files arriving for its stream — the normal CDC heartbeat); by **event creation** (section 3); or **manually** — run-now from the UI, CLI, or API (HVR's hvrstart equivalent), which is a trigger like any other and subject to the same overlap policy, so a run-now against an already-running cyclic job behaves per the stream's configured policy rather than surprising anyone.

## 5. Run Logs

Every run of every job produces a **structured run log** under a run ID: timestamped entries, the positions worked, warnings, and on failure the error with its context. Logs are retrievable from the job's page and the API (the hub-log append model, upgraded from grep-the-hub-log to query-the-run), retained per the retention policy, and linked from everything relevant — the alert that fired references the run, the run references its event, the event references its artifacts. The 2 AM question "what exactly did this job do last night" is one click, not an ssh session.

## 6. Job Settings

HVR controls job behavior through **job attributes** configured via a dedicated command — functional, and exactly the scattered-knobs pattern this platform replaces everywhere else. Job behavior here is **structured settings** on the stream and job: schedule and calendars, overlap policy, retry curve and threshold (all owned by the scheduler spec), plus job-level operational settings — priority class (which jobs yield when an agent is saturated), resource caps (max parallel slices, max concurrent jobs per agent), and the HANGING envelope override. Same schema-validated, provenance-displayed, Git-diffable treatment as every other setting in the product; no attribute archaeology.

## 7. HVR Parity Matrix

| HVR jobs concept | This platform | Delta |
|---|---|---|
| Job = one task process (capture/integrate/refresh/compare) | Same, plus activate-plan and report jobs | Kept, extended |
| Cyclic and acyclic jobs | Same | Kept |
| PENDING / RUNNING / WAITING / SUSPENDED / HANGING / ALERTING / RETRY | Same states, same meanings | Kept — the proven core |
| DISABLED vs SUSPENDED distinction | Same distinction | Kept — the lock that survives colleagues |
| DONE / READY / ERROR / FAILED terminal quartet | SUCCEEDED / FAILED with cause (error, canceled, abandoned) | Rationalized — one place to look |
| Output appended to hub log | Structured run logs per run ID, API-retrievable | Query-the-run, not grep-the-log |
| Automatic retry on failure | Same, under the scheduler's backoff/threshold | Kept (scheduler spec) |
| Event-driven long tasks (event table + associated job) | Same pattern, structured progress, artifacts attached | Kept, upgraded |
| No first-class cancellation | Cancel endpoint; checkpoint-clean stop; cause recorded | New |
| Progress via log inspection | Structured progress: percent, table, slice, positions, ETA | New |
| Job attributes via hvrjobconfig | Structured job settings with provenance | Consistent with the settings model |
| Manage via UI / CLI / API | Same three, one API underneath | Parity rule applies |

## 8. Test Plan

Phased; standing rule applies (procedure executed, results observed, evidence archived — no procedure, no pass). Full JOB suite reruns on merges touching the scheduler, event, or job-state code. State-machine timing runs on the virtual clock with controllable job stubs (the scheduler spec's key assets, reused).

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | State machine | JOB-01, JOB-02, JOB-05 | Virtual clock + job stubs | State machine implemented | Every documented transition observed; no undocumented transition possible |
| B | Event-driven tasks | JOB-03, JOB-04, JOB-07 | Integration lab | Phase A exit; event API implemented | Event flow, cancellation, and run-now proven |
| C | Logs and settings | JOB-06, JOB-08 | Integration lab under load | Phase B exit | Run-log completeness and settings enforcement proven |

### 8.1 Methods

State-machine tests are exhaustive by construction: a scripted driver walks stubs through every documented transition (including the awkward ones — HANGING that recovers, SUSPENDED during RETRY, DISABLED attempted-resume) and asserts both that each occurs and that the API reflects it within one poll interval; a fuzzing pass then attempts undocumented transitions and asserts refusal — the published diagram is the whole truth. Event tests exercise the full REST lifecycle against real long-running work (sliced refreshes in the lab), with cancellation fired at randomized points to prove checkpoint-clean stops. Log tests verify completeness against scripted ground truth and the linkage chain (alert → run → event → artifact). Settings tests saturate an agent and assert priority and cap enforcement from observed concurrency.

## 9. Test Procedures

### JOB-01 — State machine conformance and closure
**Steps:** (1) Drive a stub through every documented transition: PENDING→RUNNING→PENDING (cyclic); →SUCCEEDED (acyclic); failure→ALERTING→RETRY→RUNNING; retry-threshold→FAILED(abandoned); RUNNING→HANGING→PENDING (recovers); SUSPENDED from PENDING and from RETRY, resume from both; DISABLED, attempt ordinary resume (must refuse), re-enable. (2) Poll the API at 1s throughout; assert every transition visible within one interval with its cause event. (3) Fuzz: attempt every undocumented transition via API; assert refusal.
**Expected:** All documented edges observed; all undocumented edges refused; event log carries a caused entry per transition.
**Evidence:** Transition timeline vs script, fuzz refusal log.

### JOB-02 — Cyclic vs acyclic lifecycle
**Steps:** (1) Run a cyclic compare on a virtual-clock cadence for 10 simulated cycles; assert PENDING↔RUNNING cycling and no terminal state. (2) Run an ad-hoc (acyclic) compare; assert PENDING→RUNNING→SUCCEEDED and that the job leaves the active list per documented behavior while its runs and event remain queryable.
**Expected:** Both lifecycles exactly as documented; the acyclic job's history survives its completion.
**Evidence:** State timelines, post-completion queries.

### JOB-03 — Event-driven task flow
**Steps:** (1) POST a compare event against a large lab table (sliced); record the immediate response (event ID, sub-second). (2) Poll the event: assert structured progress advances (percent, current table, slices done) and matches the slice map. (3) On completion, assert terminal state and the attached report artifact; verify the identical flow via CLI (parity).
**Expected:** Immediate return; truthful monotonic progress; artifact attached; UI/CLI/API equivalence.
**Evidence:** Response timing, progress samples vs slice map, artifact linkage.

### JOB-04 — Cancellation, checkpoint-clean
**Steps:** (1) Start a sliced refresh event; cancel at a randomized mid-run point (repeat 5×). (2) Assert the job stops at a slice boundary (no torn slice), the event terminates FAILED(canceled), staging/live state per the refresh spec (prior data intact). (3) Resume/rerun; compare.
**Expected:** All 5 cancels clean at checkpoints; causes recorded; rerun converges (compare clean); no orphan processes on the agent.
**Evidence:** Cancel timelines, slice-boundary audits, compare reports, agent process audit.

### JOB-05 — Suspend/resume vs disable/enable
**Steps:** (1) Suspend a cyclic integrate under load; assert data movement stops at a checkpoint and state shows SUSPENDED; resume; drain; compare. (2) Disable the same job; attempt resume (must refuse with the documented message); re-enable; verify normal cycling. (3) Verify a suspended job's triggers queue/skip per the overlap policy while suspended.
**Expected:** Suspend is checkpoint-clean and resumable; disable refuses ordinary resume; trigger handling during suspension matches the configured policy; compare clean after all of it.
**Evidence:** State/wire timelines, refusal message, compare report.

### JOB-06 — Run logs and the linkage chain
**Steps:** (1) Run a scripted job sequence including one seeded failure. (2) Retrieve each run's structured log via API; diff against scripted ground truth (steps, positions, the seeded error with context). (3) Follow the chain from the fired alert → run log → event → artifact; verify every link. (4) Verify retention over simulated weeks.
**Expected:** Logs complete and accurate; the failure's cause is in the log and the FAILED cause field agrees; every link in the chain resolves; retention enforced.
**Evidence:** Log-vs-script diffs, link traversal record, retention audit.

### JOB-07 — Manual run-now parity and overlap interaction
**Steps:** (1) Trigger run-now on a PENDING job via UI, CLI, and API; assert identical behavior. (2) Trigger run-now against a RUNNING cyclic job under each overlap policy (skip, queue-one, kill-and-restart); assert policy-conformant outcomes (scheduler SCH-04 alignment).
**Expected:** Three invocation paths equivalent; run-now respects overlap policy exactly — no privileged bypass.
**Evidence:** Invocation transcripts, per-policy outcome tallies.

### JOB-08 — Priority and resource caps
**Steps:** (1) Configure agent max-concurrent-jobs=2 and a priority class ordering; queue 5 jobs (mixed priorities) against one agent. (2) Observe execution: concurrency never exceeds 2; higher priority runs first; a capped sliced refresh honors its max-parallel-slices. (3) Verify the settings' provenance display.
**Expected:** Caps and ordering enforced from observed concurrency; slice parallelism capped; settings shown with provenance like all others.
**Evidence:** Concurrency timeline, slice-worker counts, settings capture.

## 10. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| JOB-01 | Every documented state transition is observable via API within one poll interval with a caused event; undocumented transitions are refused — the published diagram is closed |
| JOB-02 | Cyclic jobs cycle PENDING↔RUNNING without terminal states; acyclic jobs terminate with queryable history |
| JOB-03 | Event-driven tasks return an event ID immediately, report truthful structured progress, and attach their artifacts on completion, identically via UI, CLI, and API |
| JOB-04 | Cancellation stops work at a checkpoint boundary with cause recorded, prior data intact, and clean convergence on rerun |
| JOB-05 | Suspend is checkpoint-clean and resumable; disable refuses ordinary resume until explicit re-enable; compare clean throughout |
| JOB-06 | Every run has a complete, accurate, retained structured log; the alert → run → event → artifact chain resolves at every link |
| JOB-07 | Run-now behaves identically from all three surfaces and obeys the overlap policy without privileged bypass |
| JOB-08 | Priority classes and resource caps (agent concurrency, slice parallelism) are enforced as observed, with settings provenance displayed |

## 11. Open Questions

Default priority classes (should capture/integrate always outrank ad-hoc compares, or is that per-hub policy?) need a decision with early operators. Whether canceled events should support direct resume (continue from checkpoint) versus rerun (new event, checkpoints made it cheap) per task type needs a per-type table before the API freezes. Run-log verbosity levels and their storage budget on busy hubs need lab numbers.
