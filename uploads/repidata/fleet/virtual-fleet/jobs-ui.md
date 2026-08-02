# Jobs — Console Surface

**Project:** Enterprise CDC Replication Platform
**Document type:** UI design specification
**Status:** v1 design — prototyped in `Replicator UI.dc.html`, wireflow in `Jobs Wireflow.dc.html`
**Related:** `jobs.md` (the job model and scheduler contract), `events.md` (the ledger), `scheduler.md`, `virtual-fleet-ui.md`, `timeline.md`, `alerts-ui.md`

---

## 1. Purpose

Jobs is **the open set**: what the scheduler is doing right now, what it is waiting on, what it is retrying, and — critically — **what should be running but is not**.

It answers one question: *what do I act on now?*

Events answers a different one: *what happened, and prove it.* Two screens, because the questions are different. But never two truths.

## 2. The model — one record, two tenses

**A job is an event that has not closed yet.**

| | Jobs | Events |
|---|---|---|
| Tense | Present | Past |
| Contents | The open set | The closed set |
| Sort | By urgency | By time |
| Mutability | Live | Immutable |
| Carries | Actions | Evidence (artifact, attribution, duration) |
| States | RUNNING · WAITING · RETRY · SUSPENDED · DISABLED · MISSING | DONE · FAILED · CANCELED |

Same id, one state machine, one row builder. **A job that finishes does not write an event — it becomes one.** This eliminates the class of bug where a job reports FAILED and the ledger reports DONE.

It also explains the behavior already in the console: an event-driven compare or refresh **holds a job** in the scheduler for as long as its event is CURRENT or WAITING, and cancelling the event drains the job.

**The timeline is where the two tenses reconcile** — both screens link into it at their own timestamp, so open conditions and closed history read against each other on one axis.

## 3. Scope

Scoped like Connections and Events: opened at virtual-fleet level, Jobs shows every job in the VF; opened from a stream, it narrows to that stream's jobs. One scope rule across all three VF screens, so a count shown at a higher level always matches what the screen it opens contains.

## 4. The list

### 4.1 Reconciliation, not enumeration

**Silence reads as health.** A capture job that died leaves no row; the list looks calm while the stream is dead. So the screen does not list what exists — it **reconciles against what is owed**.

Every activated, non-suspended stream owes the scheduler a **capture job** and an **apply job**. A job that is owed and absent renders as a red **MISSING** row, sorted to the top, naming the connection it was expected on:

> `sensor-ingest-capture` · **MISSING** · *expected on ORA-SENSORS · registered, then dropped*

MISSING is a first-class state, not an error decoration. It is the single highest-value row this screen can produce.

### 4.2 Columns

| Column | Content |
|---|---|
| — | Selection checkbox |
| Job | Job name (mono) |
| Stream | Owning stream, links to the stream page |
| Type | CAPTURE / INTEGRATE / COMPARE / REFRESH pill, with the trigger beneath (continuous / scheduled / event-driven) |
| Shape | cyclic / acyclic |
| State | State pill, HANGING badge where applicable, **plus a second line** (§4.3) |
| Detail | What it is doing, in plain words |
| — | `timeline →` plus the row's available actions |

### 4.3 No state chip stands alone

A bare state chip is anxiety. Every non-steady state carries a second line saying **where it is in its own curve**, so an operator can distinguish "recovering" from "stuck" without opening a log.

| State | Second line |
|---|---|
| **RETRY** | `attempt N of M · next in T · failing for D` — the same 30s → ×2 → 15m / 8-attempt curve used for alert delivery, reused |
| **WAITING** | The reason it waits, plus queue position where it is behind others |
| **RUNNING** | `up D · N cycles` — or **`no progress for D`** when hanging |
| **SUSPENDED / long runs** | A real progress bar: segments or slices done / total, with percent |
| **MISSING** | The connection it was expected on, and whether it was never registered or dropped |

RUNNING for forty minutes with no progress signal is indistinguishable from hung. Cyclic jobs report uptime and cycle count; acyclic jobs report completion progress.

### 4.4 The queue

A bare WAITING chip is the least useful state in any scheduler. Each waiting job names its **reason** and, where queued behind others, its **position**:

- `schedule` — next fire time
- `slot` — scheduler slot, N of M in use
- `lock` — held by another job
- `dependency` — a job that has not finished

Slot exhaustion is worth surfacing hardest: four refreshes queued behind four running ones is a **capacity** problem, not a fault, and the console says so rather than letting it read as a stall.

## 5. Actions

### 5.1 Row actions — three verbs, three meanings

| Action | Meaning |
|---|---|
| **Suspend** | Graceful. Finishes the current cycle, drain progress visible, checkpoint held. Resuming redoes at most one cycle and never loses correctness |
| **Disable** | The administrative lock that survives colleagues. An ordinary resume **refuses**; explicit re-enable is required |
| **Resume / Re-enable** | Returns to RUNNING from the last checkpoint |
| **Open event / Open window** | Event-driven work is not suspended here — it is cancelled from Events, which drains the job |
| **timeline →** | Lands on the stream timeline at this job's timestamp. This is the reconciliation link |

### 5.2 Bulk actions — never a count without a blast radius

"Suspend 6 jobs" is meaningless. The bulk bar states **which streams stop moving** before the operator commits:

> **3 jobs selected** — stops movement on 2 streams: erp-financials, mfg-workorders · 1 not directly controllable (event-driven — cancel from Events)

One selection model covers **every** row — seeded, derived, and event-driven alike — so the checkbox behaves identically regardless of which builder produced the row. Rows that cannot be directly controlled are counted and named rather than silently skipped.

Bulk suspend is graceful per job, not a kill, and writes **one** ledger event naming every job and stream affected.

## 6. Job kinds and shapes

| Kind | Shape · trigger | Notes |
|---|---|---|
| **CAPTURE** | cyclic · continuous | Reads the source log indefinitely. One per activated stream. Its absence is the MISSING case |
| **INTEGRATE** | cyclic · continuous | Applies the file log on its cadence. One per activated stream |
| **COMPARE** | acyclic · scheduled or event-driven | Runs to completion; event-driven ones are held by their event |
| **REFRESH** | acyclic · scheduled or event-driven | Runs to completion, segmented and resumable; cancel keeps loaded segments |

**Cyclic versus acyclic is the useful split**, not scheduled versus manual. A cyclic job is judged by whether it is *keeping up*; an acyclic one by whether it will *finish*. They need different progress signals, and the list gives each the one that applies.

## 7. What Events gains from the unified model

Because a closed job *is* an event, Events becomes the evidence layer rather than a second feed:

1. **Filter by artifact type** — plan diff, compare report, run log, export, enrollment token. Auditors search by artifact, not by time.
2. **Stated retention window** — a ledger with no retention policy is not an audit ledger. State the window and what happens at its edge.
3. **Signed export** — a range export the auditor can verify off-platform. A real gap for regulated buyers.
4. **Diff view on definition changes** — ACTIVATE and config-save events open the actual before/after, not a summary line.

## 8. Rules this screen holds to

1. A job and its event are one record; a finished job becomes an event.
2. Absence is a red row — the list reconciles against what is owed, it does not enumerate what exists.
3. No state chip stands alone; each says where it is in its own curve.
4. Suspend is graceful and resumable; disable survives colleagues.
5. Bulk actions state their blast radius before they run.
6. Event-driven work is cancelled from Events, never killed here.
7. Every state change is ledgered with previous → new state.

## 9. Acceptance criteria

| ID | Criterion |
|---|---|
| JBS-1 | A finished job appears in Events carrying the same id, with no state disagreement between the two screens |
| JBS-2 | Every activated, non-suspended stream is reconciled against an expected capture job and apply job; an owed-but-absent job renders as MISSING, sorted to the top, naming its expected connection |
| JBS-3 | A RETRY job displays attempt number, maximum, time to next attempt, and total failing duration |
| JBS-4 | A WAITING job displays its wait reason and, when queued, its position |
| JBS-5 | A RUNNING cyclic job displays uptime and cycle count; one making no progress displays the stalled duration and a HANGING badge |
| JBS-6 | An acyclic job in progress displays a completion bar with done/total units and percent |
| JBS-7 | Selection works identically on seeded, derived, and event-driven rows |
| JBS-8 | The bulk bar names the affected streams and the count of non-controllable rows before any action runs |
| JBS-9 | Bulk suspend is graceful per job and writes one ledger event naming every job and stream affected |
| JBS-10 | Suspend holds the checkpoint; resume redoes at most one cycle. Disable refuses an ordinary resume until explicitly re-enabled |
| JBS-11 | Event-driven rows offer Open event / Open window, never Suspend |
| JBS-12 | Every row links to the timeline at its own timestamp, at stream, VF, fleet, and global scope |
| JBS-13 | Jobs scope follows the one VF scope rule — counts shown at a higher level match the screen's contents |
