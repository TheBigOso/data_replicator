# Run history — Compare and Refresh (as prototyped)

**Project:** Enterprise CDC Replication Platform
**Surface:** Compare history and Refresh history panels
**Status:** Prototyped in `Replicator UI.dc.html`

---

## 1. One record, four scopes

A compare or refresh run is a **ledger event**, not a display row. The console shows the same records at four levels, each narrowing by what the screen owns:

| Screen | Shows | Source |
| --- | --- | --- |
| **Virtual fleet dashboard** | Every compare/refresh run in the fleet — stream-level and table-level, all streams | `fleetRunHistory(kind)` |
| **Stream (stream) dashboard** | The stream's own bulk runs only (`!e.table`) | `runHistory(pipeId, kind)` |
| **Tables screen** | Table-level runs for whatever is in view — one stream when the stream filter is set, every stream in the fleet when it is "All streams" | `tablesScreenRunHistory(kind)` |
| **Table detail** | Runs scoped to that one table | `tableRunHistory(identity, pipeId, kind)` |

Because all four read the ledger, a run started from the Compare or Refresh button appears immediately in every panel whose scope contains it.

## 2. Row anatomy

Built by one function — `runRow(event)` — so every panel is identical:

| Part | Content |
| --- | --- |
| State pill | `CURRENT`, `WAITING`, `CANCELED`, `FAILED`, or `DONE/IDENTICAL` · `DONE/DIFFERENT` · `DONE/INCONCLUSIVE` for compares |
| Scope | The event text — *Bulk compare of 64 tables*, *Row-wise refresh of WORKORDERS* |
| Stream badge | Fleet and Tables panels only, since those cross streams |
| Time | Relative (`48m ago`, `yesterday`, `6d ago`) via `agoLabel(ts)` |
| Result · duration · actor | Outcome from the event's `outcome` detail, duration via `durLabel(ms)`, and who started it (operator or `scheduler`) |

**Ordering.** Running first, then scheduled, then completed newest-first: `rank(state) → ts desc`. Anything CURRENT is always at the top of the list.

## 3. Clicking a run hands off to the ledger

Rows are not expanded in place. Clicking one calls `openEventFromHistory(id)`, which:

1. switches to **Events**,
2. clears the stream filter (`selected: null`) so an older run is in scope,
3. sets `evOpen[id] = true` so that event is expanded, and
4. scrolls it into view — Events rows carry `data-event-id`, and the handler walks up to the scrolling pane and positions the row 80px below the top.

This is deliberate: the history panel is an index, the ledger is the record. There is one place where a run's parameters live, and it is the event.

## 4. State on a compare is DONE; the outcome is a field

Compare runs store `state: 'DONE'` with `outcome: 'IDENTICAL' | 'DIFFERENT' | 'INCONCLUSIVE'` and an `outcomeKind` for the pill colour.

The run completed — that is what its state says. Whether source equalled target is a *result*, carried in the event's `outcome` detail and rendered by the history panels as `DONE/DIFFERENT` in red. Keeping the two apart means the Events state filter (`CURRENT`, `CANCELED`, `DONE`, `FAILED`, `WAITING`) still selects every run, and the DONE pill never claims a mismatch was a success.

## 5. Seeded history

Two generators produce the record a fleet would already have, cached once per session:

| Generator | Produces |
| --- | --- |
| `seedRunEvents()` | 5 compares + 5 refreshes per stream — bulk runs, no `table` field |
| `seedTableRunEvents()` | Per table: 3 compares and 2 refreshes, each carrying `table`, the fully qualified source name, and the derived target name |

Both are deterministic — a hash of stream (and table) name drives granularity, session count, outcome, duration, and actor — so the same fleet reads the same way on every load.

**The newest table run agrees with the pill in the Tables list.** A table showing `BUSY/DIFFERENT` gets a CURRENT compare at the top of its history; `DONE/DIFFERENT` seeds a DIFFERENT outcome; `NONE` or `PENDING` seeds no runs at all and the panel says *"This table has never been compared."* The list and the history cannot disagree.

**Event ids are unique.** Ids are `String(ts * 1000 + suffix)` where the suffix is an incrementing per-run counter and `ts` is offset by a per-stream hash — two streams can never land on the same id, which would otherwise expand or cancel the wrong record.

## 6. Where it lives in the prototype

| Concern | Location in `Replicator UI.dc.html` |
| --- | --- |
| Seeded stream runs | `seedRunEvents()` |
| Seeded table runs | `seedTableRunEvents()` |
| Shared row builder | `runRow()`, `agoLabel()`, `durLabel()` |
| Scope queries | `runHistory()`, `tableRunHistory()`, `tablesScreenRunHistory()`, `fleetRunHistory()` |
| Ledger handoff | `openEventFromHistory()`; `data-event-id` on Events rows |
| Panels | Template blocks marked `HISTORY PANELS` on the fleet, stream, tables, and table-detail screens |
