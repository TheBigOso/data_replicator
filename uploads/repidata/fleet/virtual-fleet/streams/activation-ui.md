# Activation — Console Surface

**Project:** Enterprise CDC Replication Platform
**Document type:** UI design specification
**Related:** `stream.md` §6 (components for activating replication), `refresh.md` (initial load / reload / repair), `alerts-ui.md`, `tables-ui.md`

---

## 1. Principle — activate first, refresh rides the plan

**Activate replication** is the stream's primary action; there is no standalone Refresh button. Refresh only runs *chained off the activation plan*: activation establishes the capture position (snapshot position **S**), then the refresh reads as-of that same position and integrate skips captured changes ≤ S per refreshed table — capture and load always meet with **no gap and no double-apply**, and nothing is suspended while it runs.

HVR ships activation as `hvractivate` and refresh as a separate `hvrrefresh`; our departure is that the console makes the safe ordering the only ordering, and the plan explains itself before it runs.

## 2. Entry points and scope

- **Stream header → `Activate…`** and **Stream admin → `Activate replication…`** open the same dialog.
- The dialog is scoped to the **virtual fleet you are in** — shown as a static label, no fleet picker. A **Stream** select lists the fleet's streams (alphabetical); opening from a stream page preselects that stream.
- Switching stream resets fetched state (sequences, open-txn counts, table selection).

## 3. Table scope

Streams can hold hundreds of tables, so the plan is table-scopable:

- Checklist of registered objects (identity + name in source), alphabetical, scrollable, **all selected by default**. Header count: `61 of 63 registered objects selected`.
- **Filter box** (matches identity or source name), **Select all**, **Unselect all**.
- Partial selection scopes everything downstream: component work, the chained refresh, the CLI (`--tables a,b,c,+N`), and both ledger events. Zero selected blocks apply.
- A stream with no registrations shows a note instead of the checklist.

## 4. Computed plan — replication components

The plan is computed from the definition against the live locations. Component rows (full row clickable; fixed rows don't toggle):

| Component | First activation | Active stream (verify plan) |
|---|---|---|
| Jobs | always applied — capture + integrate registered under the scheduler | same; recreated on every definition change |
| Table enrollment | will snapshot | verified · current — per-table incremental, only stale tables re-enroll; optional **replace all old enrollment** |
| Supplemental logging | will enable | verified · in place — idempotent |
| State tables | will create (commit positions, loopback protection) | in place — kept; recreation is destructive and lives behind its own guarded row |
| Capture position | will set (per §5) | held — a verify plan never resets the position |

Status pills flip with stream state (warn-amber "will …" vs neutral "verified/held").

## 5. Capture start (first activation only)

Five modes; on an active stream the section reads "Held — already positioned; a rewind is its own guarded plan on the Stream Timeline."

1. **Now** — current source position; no rewind into the logging stream.
2. **Rewind to the oldest open transaction, emit from now** — covers long-running transactions without re-sending applied changes. Shows "Source currently has *N* open transactions" with a **Fetch again** re-query.
3. **Rewind back an interval, emit only changes committed from now** — minutes input; covers transactions longer than the interval.
4. **Recovery rewind to the target's integrate sequence** — hub-failover path; the position lives on the target, not the hub. **Fetch sequence…** opens a sub-dialog:
   - *Previous stream used different names* — previous stream + previous capture-location name inputs, plus a per-location previous-name field on each row (for renamed setups).
   - *Select integrate locations* — checklist; with multiple targets the rewind uses the **oldest** integrate sequence.
   - Result pins next to the radio: `seq 0x3A81F2 · committed 22:41 · state table on databricks-lh`; required before apply.
5. **Custom rewind…** — `YYYY-MM-DD HH:MM` plus an **emit policy**: committed after the rewind time / committed from now / delayed until a source position (tx seq / SCN).

## 6. Initial load, start policy, CLI

- **Load the target after activation** (default on) — refresh of the selected tables, chained off snapshot S.
- Method: **Bulk** (stage + atomic swap) or **Row-wise** (repair only differences).
- Target tables: **leave untouched** or **truncate and load**.
- **Start policy:** start jobs after apply, or leave suspended. Starting resumes a paused stream.
- An equivalent-CLI line mirrors every choice, e.g.
  `repl activate stream-east db2-mfg-copy --components jobs,enroll,suplog --capture-start now --tables bom_components,machine_events,+59 --refresh bulk --target untouched --start`

**Gates on apply** (toast names the fix; dialog stays open): ≥1 table selected · custom rewind needs a position · recovery needs a fetched sequence · interval needs minutes > 0.

**Outcome:** an `ACTIVATE` ledger event (plan, tables, components, capture start, load, start policy, CLI) plus a chained `REFRESH` event. Both land at the top of the stream's **Recent events** (live actions merge with the seeded ledger, newest first) and on Events.

## 7. Stream log — the live reading surface

Docked on the stream page below Tables (above Compare history); the same chrome floats as an overlay.

**Line anatomy** — timestamp · job name · payload:
- Capture: `Captured 177 rows from 96 seconds ago for 'OPERATORS' (89 upd, 88 ins). This took 4.50 seconds.` and cycle lines (`Capture cycle scanned 2 transactions (226,435 bytes)… routed 3,008 bytes (compression=95.5%)… Capture cycle 426.`)
- Integrate: `Integrate cycle 417 for 1 transaction file…`, `Integrated 211 changes… — end-to-end latency 96s.`
- Errors/suspensions render amber and explain themselves (`stream suspended — jobs drained at their checkpoints…`).

**Tabs** — visiting a stream page opens (and activates) its `<stream>.out` tab; click switches, ✕ closes; the set persists (`repl-stream-logs`). The overlay shows whichever tab is active — watch stream A while working on stream B.

**Control row** (second row, under the tabs): far-left **⇱ Overlay / ⇲ Dock in page**, then **Copy** (flips to "✓ Copied" + toast), **Download** (`<stream>.out.log`), **⏸ Pause / ▶ Follow**. Right-aligned filter chips: **Capture · Integrate · Latency · Errors**, all on by default — a line shows if any of its tags is on; all-off shows a hint; Copy/Download export exactly what's visible.

**Modes** — docked (default) ⇄ overlay (fixed bottom strip from sidebar edge to screen right, tracks sidebar resize, follows across screens; the page gains bottom padding so content scrolls clear) ⇄ minimized (▼ collapses to the tab bar, ▲ restores). Mode and minimized state persist (`repl-stream-log-mode`, `repl-stream-log-min`); while floating, the page shows a dashed "⇲ Dock in page" placeholder.

## 8. Requirements

| ID | Requirement |
|---|---|
| ACTUI-1 | Activate replication is the stream's primary action; no standalone refresh — the initial load / reload is always chained off the activation snapshot (no gap, no double-apply, nothing suspended) |
| ACTUI-2 | Dialog scoped to the current virtual fleet (static label) with an alphabetical stream select; deep-link preselects the stream |
| ACTUI-3 | Table checklist (alphabetical, all-on default) with filter, select all / unselect all; partial selection scopes plan, load, CLI, and events; zero selected blocks apply |
| ACTUI-4 | Computed component rows (jobs, enrollment + replace-old, supplemental logging, state tables, capture position) with first-activation vs verify/held status pills; destructive recreation stays behind its own guarded row |
| ACTUI-5 | Five capture starts — now, oldest open txn (live count + fetch again), rewind interval, recovery via target integrate sequence (fetch-sequence sub-dialog: previous names, location checklist, oldest-sequence-wins), custom rewind with emit policy |
| ACTUI-6 | Chained load: bulk or row-wise; target tables leave-untouched or truncate-and-load; start policy start/suspend; equivalent CLI mirrors every choice |
| ACTUI-7 | Apply gates fail as toasts naming the fix; success writes ACTIVATE + chained REFRESH ledger events that surface in Recent events (live merge, newest first) |
| ACTUI-8 | Stream log: per-stream persistent tabs; docked ⇄ full-width overlay ⇄ minimized with persisted mode; Copy (with feedback) and Download of the visible lines; Pause/Follow |
| ACTUI-9 | Log filter chips Capture / Integrate / Latency / Errors, all on by default, OR-combined per line; all-off shows a hint |
| ACTUI-10 | Log lines carry rows + table + duration on capture, changes + end-to-end latency on integrate; errors and suspensions render amber and self-explain |
