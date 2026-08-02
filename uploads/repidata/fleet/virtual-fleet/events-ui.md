# Events — Console Surface

**Project:** Enterprise CDC Replication Platform
**Document type:** UI design specification
**Status:** v1 design — prototyped in `Replicator UI.dc.html`, wireflow in `Events Wireflow.dc.html`
**Related:** `events.md` (the ledger model, API enforcement, immutability, forwarding), `jobs-ui.md`, `timeline.md`, `virtual-fleet-ui.md`, `run-history.md`

---

## 1. Purpose

Events is **the audit ledger, made readable**. `events.md` defines what the ledger *is* — append-only, API-enforced, forwardable. This document defines the surface an operator or auditor actually uses: how events are narrowed, read, expanded, and exported.

It answers one question: *what happened, and prove it.*

Jobs answers the other: *what do I act on now.*

## 2. The line the screen states

The header states the rule in one sentence, because the rule is what makes the ledger usable:

> The audit ledger — every user action that changes something is recorded with who did it, what it touched, and how it ended. Read-only activity and automated job cycles are not events; those live in the job logs.

| Is an event | Is not an event |
|---|---|
| Every **user action that changes something** — activate, suspend, disable, compare, refresh, definition change, permission grant, enrollment, export, sign-in | **Read-only activity** and **automated job cycles** |
| Scheduler-initiated work a user could have initiated | A capture cycling 18,422 times — that is one running job, not 18,422 audit records |

Get this line wrong in either direction and the ledger dies: too permissive and it becomes an unsearchable firehose no auditor will read; too strict and a change happened that nobody can attribute. The test is **"could someone be asked to justify this?"**

## 3. Relationship to Jobs

**Events is the closed set; Jobs is the open set — the same record in two tenses.** A job that finishes does not write an event, it *becomes* one, keeping its id.

That is why an in-flight compare or refresh appears here as **CURRENT** rather than as a second, separate row, and why cancelling a CURRENT event drains the job holding it. See `jobs-ui.md` §2.

## 4. Scope

Same VF scope rule as Jobs and Connections: at virtual-fleet level, every event in the VF; opened from a stream, that stream's events only.

**Arriving from a specific record scrolls to it and expands it** — from a Job's *Open event*, a Compare/Refresh history row, a stream's Recent events strip, or a timeline marker chip.

## 5. Narrowing — six filters that compose

| Filter | Kind |
|---|---|
| Streams | Named objects in this VF |
| Connections | Named objects in this VF |
| Type | SUSPEND · REFRESH · COMPARE · ACTIVATE · DEFINITION CHANGE · GRANT · ENROLL · EXPORT · SIGNIN · STOP |
| State | CURRENT · WAITING · DONE · FAILED · CANCELED |
| Started | Time range |
| Search | Free text over summary and parameters |

All six **AND** together, and **the matching count is always visible** (`All 142 matching events`) — so a narrowed view can never be mistaken for an empty ledger. That distinction is the entire reason the count is a permanent fixture rather than a footer.

**Scope filters name real objects**, not free text — a typo cannot silently return nothing.

**Event ID is the default sort, descending**, with the ▼ indicator visible on load. Because the id *is* the timestamp, sorting by id and sorting by time are the same operation — there is no way for them to disagree.

**Persistence split:** the column chooser persists per user; filters are session-only. Looking is transient; setup is a preference.

## 6. The row

| Column | Content |
|---|---|
| — | Expand caret |
| Type | Type pill with the one-line summary beneath |
| Stream | Owning stream, or `—` |
| Connections | Source → target where applicable, or `—` |
| State | State pill |
| Event ID | Microsecond-precision id, which is also the timestamp |
| Created | Relative age |
| — | **View log** |

## 7. The expanded record

Expanding a row reveals the full record: a header repeating type and id, a field strip (stream, connections, state, job, started, duration, number of retries), and the **parameter block**.

**The parameter block is the point.** A one-line summary is a headline; the parameters are what the event actually did, in the platform's own terms:

```
PARAMETERS
  job             billing-invoices-refresh
  job type        REFRESH
  current state   SUSPENDED
  detail          drained at segment 12/40 · resumable
  clears when     an operator resumes the job
```

**An open (CURRENT) event additionally states `clears when`** — so a ledger row is never a dead end that leaves the reader wondering what would close it.

## 8. The evidence

Every event points at its artifact:

| Type | Artifact |
|---|---|
| ACTIVATE | The applied plan diff |
| COMPARE | The compare report, per table |
| REFRESH | The run log with segment detail |
| DEFINITION CHANGE | The versioned before/after |
| EXPORT | The export manifest |
| ENROLL | The token record |

**View log** opens the job log **positioned at that event's timestamp** — not the top of the file. An audit trail that makes you scroll for the moment is not a trail.

## 9. Planned upgrades

These follow from treating Events as the evidence layer rather than a feed. None is built yet.

### 9.1 Filter by artifact

"Show me every compare report from Q2" is the actual auditor question; today it can only be reached by combining Type and a date range and hoping. A seventh filter makes it direct:

`any artifact · plan diff · compare report · run log · export manifest · token record · has no artifact`

**"has no artifact" earns its place too** — it is how you find events that changed something but left no evidence, which is exactly what an audit should surface.

### 9.2 Retention, stated on the screen

A ledger with no retention policy is not an audit ledger. `events.md` §5 defines retention as a configured, evented setting; the screen must **state it where it is read**:

| Field | Example |
|---|---|
| retained | 36 months (regulated default) |
| oldest held | 2024-02-11 · 29 months |
| at the edge | archived to the hub file store, not deleted |
| artifacts | retained with their event, same window |
| set by | Global Admin · applies fleet-wide |

An auditor reading a 14-month-old event needs to know whether the 20-month-old one still exists. And **what happens at the edge** matters as much as the number: archived and retrievable is a different promise from deleted.

### 9.3 Signed export

An export the auditor can verify **without trusting the console that produced it**. A real gap for defense and regulated buyers, and the one place a screenshot is not evidence.

| Field | Value |
|---|---|
| range | The current filter, stated in full |
| format | JSONL + a manifest |
| signature | Detached, over the manifest digest |
| includes | Artifacts by reference, with digests |

**The export is itself an event** — EXPORT, attributed, with the filter it ran under recorded. Exporting the audit log is an auditable act.

This is the practical near-term form of the cryptographic-chaining question left open in `events.md` §10: signing an exported range is cheaper than chaining every record, and covers the accreditor's actual ask.

### 9.4 Diff view on definition changes

ACTIVATE and DEFINITION CHANGE events summarize: *"Column DISCOUNT_PCT dropped from GL_JOURNALS."* The reviewer's next question is always **what else was in that change**.

```
tables.GL_JOURNALS
− column DISCOUNT_PCT NUMBER(5,2)
+ apply.style history
  compare.schedule nightly → hourly
```

The versioned definition already exists — this only surfaces it. It is the same diff the activation plan showed before it was applied, so **plan and record are the same artifact**.

## 10. Events in the four-level hierarchy

| Level | How events appear |
|---|---|
| **Stream** | The "Recent events" strip — a **preview of the ledger**, not a second source. Same ids, same attribution |
| **Virtual fleet** | The full ledger, with all filters and the expandable record |
| **Fleet** | Markers in the fleet log; condition chips on VF cards |
| **Global** | Only triage-worthy events, in the needs-triage strip and its 90-day history |

**One ledger, four viewports.** No level keeps its own copy, so a count at any level is a filtered read of the same records — which makes "the number here matches the number there" true by construction rather than by discipline.

## 11. Rules this screen holds to

1. Every change is an event; no read or job cycle is.
2. Attribution is never blank — a named person or the scheduler.
3. Events are immutable; a correction is a new event.
4. The id is the timestamp, so sort order can never disagree.
5. The matching count is always visible — filtered is not empty.
6. An open event states what would close it.
7. View log opens at the event's moment, not the top of the file.
8. Exporting the ledger is itself a recorded event.

## 12. Acceptance criteria

| ID | Criterion |
|---|---|
| EVU-1 | The header states what is and is not an event; no read-only action or automated job cycle produces a row |
| EVU-2 | An in-flight compare or refresh appears as a single CURRENT event, not as a separate job-shaped duplicate; its id matches the Jobs row holding it |
| EVU-3 | All six filters compose with AND, and the matching count is visible at all times |
| EVU-4 | Scope filters offer named objects from the current VF; free-text search is separate |
| EVU-5 | Default sort is Event ID descending with the indicator visible on load; id order and time order are identical by construction |
| EVU-6 | Column visibility persists per user; filter selections are session-only |
| EVU-7 | Expanding a row reveals the field strip and the parameter block in platform terms, not a restated summary |
| EVU-8 | Every CURRENT event states `clears when` |
| EVU-9 | Every event with an artifact links to it; View log opens the job log positioned at the event's timestamp |
| EVU-10 | Arriving from a Job, history row, or timeline marker scrolls to that event and expands it |
| EVU-11 | *(planned)* Artifact type is a filter, including "has no artifact" |
| EVU-12 | *(planned)* Retention window, edge behavior, oldest held record, and owner are stated on the screen |
| EVU-13 | *(planned)* A filtered range exports as JSONL + signed manifest with artifact digests, and the export is itself recorded as an EXPORT event naming its filter |
| EVU-14 | *(planned)* ACTIVATE and DEFINITION CHANGE events open the versioned before/after diff — the same artifact the plan showed |
