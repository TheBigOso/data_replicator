# Stream — Console Surface

**Project:** Enterprise CDC Replication Platform
**Document type:** UI design specification
**Status:** v1 design — prototyped in `Replicator UI.dc.html`, wireflow in `Stream Wireflow.dc.html`
**Related:** `stream.md` (the stream model, replication styles, activation), `virtual-fleet-ui.md` (the level above), `tables.md` / `tables-ui.md`, `activation-ui.md`, `compare-ui.md`, `refresh.md`, `run-history.md`, `timeline.md`, `jobs-ui.md`, `events-ui.md`
**History:** absorbed `add-table-ui.md` and `streams-duplicate.md` (2026-08-01) — both were single-modal sub-flows of this screen.

---

## 1. Purpose

The Stream page is **the leaf** of the four-level hierarchy (Global Fleet → Fleet → Virtual Fleet → **Stream**).

A stream is one replication unit: a source, a target, a table set, and a mode. It is the smallest thing that can be activated, compared, refreshed, paused, or retired. `stream.md` defines the model; this document defines the screen.

Opening a stream **opens its log tab** automatically and makes it active; the tab persists after navigating away.

### 1.1 Entry points

| From | Action |
|---|---|
| VF page | A row in the stream table |
| Sidebar tree | VF → Streams → id |
| Global triage | A channel-error or latency row, context switched in |
| Connection detail | A stream-membership row |

## 2. The lifecycle this page owns

```
New stream → Suspended · not activated → Activate (plan) → Apply + chained refresh
   → Healthy · capturing ⇄ Compare / Refresh ⇄ Add / remove tables
   → Suspend → Deactivate / retire
```

**Any change to the definition** — tables added, method changed, connection swapped — re-enters at **plan**. There is no path in the console that mutates a running stream without a diff first.

## 3. Layout

### 3.1 Header

Breadcrumb to the owning VF, then the stream name, status pill, and three actions: **Stream Timeline · Duplicate · Pause/Resume**. A sub-line names the VF, the capture and apply mechanisms, and the registered table count.

**Pause is honest.** A paused stream reports Suspended, zero rows, no latency, and its capture position is **held** — resuming picks up exactly where it stopped, no refresh required.

### 3.2 The three-stage strip

**Capture → File log → Apply**, always in this order, each naming its connection and its current position.

The strip is the mental model. When a stream breaks, the stage that broke is the one showing the error text — an operator reads the failure point before reading any log.

### 3.3 Latency panel

Latency over the last 30 minutes with a sparkline, rows/min, and a **"why? → stream timeline"** link. The link is not decoration: latency without a cause is a number, so the panel always offers the timeline that explains it.

### 3.4 Recent events

A short strip of the most recent ledger entries for this stream. It is a **preview of the ledger, not a second source** — same ids, same attribution, each row opening its full record in Events.

### 3.5 Tables

Per-table state, not a name list: identity, name in source, group, **recent refresh**, **recent compare**, average changes, and volume/day. "The stream is healthy" can therefore be checked row by row.

Row actions: compare this table · refresh this table · remove from stream. The volume unit (rows / MB / GB) is a **per-user preference** shared with the Tables page.

**Removing a table** stops replication for it at the next checkpoint and asks whether in-flight changes drain through apply or are discarded. Other tables keep running — a table is not a stream.

## 4. Add tables

*(absorbed from `add-table-ui.md`; `tables.md` owns the registration concept, `tables-ui.md` owns the Tables screens.)*

### 4.1 Entry points and scope

Two ways in, one dialog:

- **Tables toolbar · Add table** — the stream is the active stream filter; with the filter on *All streams*, the selected stream.
- **Stream page · Tables section · Add table** — always that stream.

The dialog is scoped to **one stream**. Registration keys on `stream·identity`, so a duplicated stream registers (and removes) its own copy independently of the origin.

### 4.2 The source catalogue

The dialog reads the stream's source schema as capture would: every table in the schema, minus those already registered in this stream. Header cards name both sides before anything is picked: **Source system** (capture agent, dialect, database) and **Target** (apply agent, dialect, "objects created on first refresh").

### 4.3 Step 1 — Pick

Search (identities and physical names), **Select all *n*** (selects the *filtered* rows), **Clear**. Each row: checkbox, identity, fully qualified physical name, row estimate, column count. Footer: `n selected · x of y shown`.

**Flagged rows are registrable, but warned** — that guardrail is the point of the catalogue view:

| Flag | Meaning |
| --- | --- |
| `no primary key — apply would match on all columns` | Slow and unsafe on updates/deletes; fix with a key or unique index |
| `supplemental logging not enabled on the source` | The source can't produce before-images until the dialect's enable statement runs (shown verbatim in the table detail's source DDL pane) |

**Empty state:** "Nothing left to add — every table in this schema is already registered."

**Gate:** ≥ 1 table selected → **Review *n* tables**; otherwise a toast and the dialog stays put.

### 4.4 Step 2 — Review ("Confirm what goes online")

Registering a table starts capture, so the operator confirms an explicit list rather than whatever the checkboxes held:

- One row per picked table: identity, row/column meta, `source → target` name mapping, per-row **Remove** (unpicks; Back to the catalogue keeps the remaining checkboxes).
- A flagged note: "*n* of them need attention before they replicate cleanly" or "None of them are flagged; all have a key and capture-ready logging."
- The consequence panel, verbatim: on confirm the definition is written, capture starts at the next checkpoint, target objects are created on the first refresh — **nothing is copied until that refresh runs**.

**Cancel / ✕ at any step** discards the selection; nothing is registered.

### 4.5 What Register does

Registration is a definition change, never a data copy:

1. Rows land in the Tables grid immediately — state **Queued**, refresh **PENDING**, compare **NONE**, volume `—`.
2. A **DEFINITION CHANGE** event records: object, the added identities, source schema, `capture: starts at the next checkpoint`, `initial load: refresh required before rows appear on the target`, and `flagged:` naming any warned tables (or `none`).
3. Toast: "*n* tables registered in *stream* — capture starts at the next checkpoint; run a refresh to load the initial data."
4. Persisted in `repl-added-tables`; added tables behave exactly like seeded ones — qualified, cloned into duplicates, removable via stop-and-remove.

### 4.6 From registered to replicating

1. **Registered** — capture armed at the next checkpoint; the target object does not exist yet, no rows have moved.
2. **Run refresh (initial load)** — creates the target objects (per-dialect DDL, partition/cluster/sort keys chosen from surviving columns) and bulk-loads the rows. Standard refresh flow; backgroundable like any job.
3. **Capture live** — state → Replicating, refresh DONE, sparkline starts filling; changes flow with the rest of the stream, no per-table job.
4. **Verify** — compare when settled.
5. **Undo** — Remove on the row: the stop-then-remove flow, specified in `tables-ui.md` §3a.

A registered table that is never refreshed stays PENDING with volume `—` forever — the guardrail is visibility, not a blocked register.

## 5. Duplicate

*(absorbed from `streams-duplicate.md`.)*

### 5.1 Why it exists

Operators need a second stream off the same source: a test target before a mapping change, a second consumer of the same tables, a like-for-like copy pointed at a different platform. Copying a definition by hand is where drift starts, so duplication is a first-class action.

**A duplicate is a new stream, not a variant.** It shares the source capture *connection* and gets everything else of its own: log position, file log, jobs, checkpoints, statistics, and state. The original keeps running untouched — that is the whole point.

### 5.2 Where the action is

Three paths, all opening the same dialog: **Stream page** (`Duplicate` in the header toolbar), **Streams list** (a row action), **Stream admin** (`Duplicate stream…` under Operations).

### 5.3 The dialog

| Field | Behavior |
| --- | --- |
| New stream name | Defaults to `<source>-copy`, then `-copy2`… until unused. Normalised to lower case with `a–z 0–9 . _ -`; a collision is refused with the reason |
| Virtual fleet | Fixed to the source's fleet, stated rather than editable |
| Target | Radio list of target connections **in that fleet**, the source's current target first and labelled as such. A note says a different destination needs its connection created in Connections first |
| What carries over | Table registrations · column plan (renames, drops, type overrides, keys) · replication rules · schedules and jobs. The first three default on; **schedules default off** so a test copy stays quiet |
| Starting state | *Start suspended* (default — definition lands, nothing captures) or *Activate now* |

A footer states the derived target objects and that both streams read the same capture at independent log positions.

### 5.4 What creation does

1. Appends a stream record with `dupFrom` set to its source.
2. Marks it paused when it starts suspended, so the suspended presentation is *derived*, never stored.
3. Writes a `DEFINITION CHANGE` event listing every choice — source capture, target and dialect, target object pattern, what was copied, file log, starting state.
4. Lands the operator on the new stream's page.

**Suspended means nothing is moving.** Latency and rows/min read `—` with a flat chart, capture reports *own position, not started*, the file log holds 0 MB, apply is idle awaiting activation, and every copied table sits Suspended with no rows. Resume flips it all on.

### 5.5 Derived, not stored

| Property | Derivation |
| --- | --- |
| Status, latency, rows | From the original definition, walking `dupFrom` back through any chain of duplicates, then zeroed if paused |
| Tables | Clones of the origin's registrations, re-pointed at the new stream and reset to PENDING / never-compared |
| Dialects | Source dialect of the origin + dialect of the chosen target |
| Target object names | `tgtPattern` namespaced by the new stream name, so two streams never write the same objects |

A duplicate of a duplicate resolves to the original for both metrics and table registrations. Duplicates persist in `repl-dup-pipes` (`{ pipes, paused }`); older saved records heal themselves because metrics are derived rather than trusted.

## 6. Suspend, deactivate, retire — three different amounts of undo

| Action | Meaning |
|---|---|
| **Suspend** | Jobs stop, **positions held**. Resume continues exactly where it stopped. No refresh needed |
| **Deactivate** | Removes runtime components. **Retention-first defaults:** state tables and registration are kept unless explicitly dropped; supplemental logging is never dropped automatically |
| **Retire** | After the GC interval, zero files remain on the hub file store; the definition survives read-only with its full version history |

Destructive teardown is **opt-in and confirmed by typing the stream name** — never a default, never a single click.

## 7. Where this stream appears elsewhere

| Surface | How |
|---|---|
| VF page | A row with derived status, latency, and rows/min |
| VF / fleet / global logs | Its lines, job-prefixed, merged into every level above |
| Global triage | Channel errors and latency breaches, deep-linking back here |
| Connection detail | A membership row on both source and target, with the role it plays |
| Compare / Refresh history | Every run, at VF level and per-table, from one shared row builder |

## 8. Rules this screen holds to

1. Every definition change re-enters at plan — no silent mutation.
2. Status is derived from job state, never asserted.
3. Suspend holds positions; only teardown drops state.
4. A table is not a stream — removing one leaves the rest running.
5. A compare never reports a false green.
6. A duplicate shares connections but never state or history.
7. No data moves at registration; target objects appear only on the first refresh.
8. Every action shows its equivalent CLI and is ledgered.

## 9. Acceptance criteria

| ID | Criterion |
|---|---|
| STU-1 | Opening a stream opens and activates its log tab; the tab persists across navigation |
| STU-2 | The three-stage strip always renders capture → file log → apply, each naming its connection and current position; a broken stage carries the error text |
| STU-3 | The latency panel links to the stream timeline; the Recent events strip shares ids and attribution with the ledger |
| STU-4 | The Tables section shows last refresh and last compare **per table**; the volume unit is a per-user preference shared with the Tables page |
| STU-5 | Removing a table stops it at the next checkpoint, asks whether in-flight changes drain or are discarded, and leaves other tables running |
| STU-6 | Add table from the Tables toolbar targets the stream filter's stream; with *All streams*, the selected stream |
| STU-7 | The catalogue never lists a table already registered in this stream; a duplicated stream keeps its own list |
| STU-8 | Search filters by identity and physical name; Select all selects only the filtered rows |
| STU-9 | No-key and no-supplemental-logging tables are flagged in the picker, again in review, and named in the event's `flagged` field — but remain registrable |
| STU-10 | Review is mandatory: the primary action in step 1 is Review, never Register; Remove in review unpicks, Back preserves remaining selections; register with zero tables is impossible |
| STU-11 | Registered rows appear as Queued / refresh PENDING / compare NONE / volume `—`; a DEFINITION CHANGE event and toast state the checkpoint and refresh-required semantics |
| STU-12 | No data moves at registration; target objects appear only on the first refresh; registrations persist across reloads; Cancel at any step registers nothing |
| STU-13 | Duplicate defaults to an unused `<source>-copy` name, fixes the virtual fleet, lists only that fleet's target connections, and defaults schedules off |
| STU-14 | A duplicate shares the source capture connection but has its own log position, file log, jobs, checkpoints, and statistics; the original is unaffected |
| STU-15 | A suspended duplicate reports `—` latency, zero rows, 0 MB file log, and idle apply; resume turns all of it on |
| STU-16 | Duplicate metrics and table registrations are derived each render, resolving a chain of duplicates back to the original |
| STU-17 | Suspend holds capture positions; deactivate defaults to retention-first; retire leaves zero files after GC with the definition read-only |
| STU-18 | Destructive teardown requires typing the stream name |
