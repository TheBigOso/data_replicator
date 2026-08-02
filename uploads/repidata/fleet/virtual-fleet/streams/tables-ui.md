# Tables — Console Surface (as prototyped)

**Project:** Enterprise CDC Replication Platform
**Document type:** Console specification — what the prototype implements
**Relationship to `tables.md`:** `tables.md` owns the *concept* (status model, drift, adopt, table-scoped operations). This document owns the *screens* — what is rendered, what is clickable, what each control does, and where its state lives. Where the two disagree, `tables.md` wins and this file is the defect.

---

## 1. Two screens

**Tables (list)** — every table across every stream in the virtual fleet, filterable to one stream. Reached from the sidebar under a stream, or from "view all in Tables" on a stream detail page (which pre-filters to that stream).

**Table detail** — one table, everything about it. Reached by **clicking the table name** in the list. There are no per-row Edit or Drop-column buttons in the list: structural editing belongs on the detail screen, where the operator can see the whole structure they are changing. The list keeps only Remove, which is a stream-membership act rather than a structural one.

## 2. Tables (list)

| Column | Content |
| --- | --- |
| Table | The identity — clickable, opens the detail screen |
| Stream | Owning stream |
| Name in source | **Fully qualified** physical name — database, schema, table (`MFGDB.MFG.WORKORDERS`). Also clickable, opening the same detail screen |
| Group | Table group |
| Recent refresh | PENDING · BUSY · DONE (clickable — links to the run record) |
| Recent compare | PENDING · BUSY · BUSY/DIFFERENT · DONE/IDENTICAL · DONE/DIFFERENT · DONE/INCONCLUSIVE |
| Avg changes | Twelve-point sparkline over the change-volume series |
| Volume/day | Bytes moved per day in the operator's chosen unit |
| — | Remove |

**Fully qualified names.** The database component follows the source platform's convention, derived from the stream id: `pg-billing` → `billingdb.billing.invoices`, `db2-mfg` → `MFGDB.MFG.WORKORDERS`, `ora-erp` → `ERPPRD.ERP.GL_JOURNALS`. It is what an operator types into the CLI and what appears in capture logs, so the console shows nothing shorter. Duplicated streams inherit the origin's database.

**Volume/day** is derived, never stored: average change rate × an estimated row width from the table's own column definition, so a wide table moves more bytes per change and the number tracks the sparkline beside it. Tables that are suspended or have never run read `—`.

**Unit selection is the operator's, per stream.** A `Volume in` selector (Auto · KB · MB · GB · TB) sits in the Tables toolbar and, on a stream's own Tables section, beside the registered count. The choice is stored per stream (and once for the unfiltered Tables view) in `volUnits` and persists with the user's other preferences.

**One grid, two paths.** The stream dashboard's Tables section renders the *same* grid and the same row view-model as the Tables screen — same columns, pills, sparkline, clickable names, and Remove flow — so behavior cannot drift between the two ways in. Columns shrink proportionally and ellipsize; the grid only scrolls sideways below ~900px of pane width.

Controls: search across identities and physical names, a stream filter, the volume unit selector, and Add table (the full flow is specified in `stream-ui.md`). The fixture spans seven streams and eight groups (FINANCE, PROCURE, SUPPLY, SHOPFLOOR, PEOPLE, SALES, IOT), including a fully stopped stream (`mssql-hr`) so the dead-table case is visible rather than theoretical.

## 3. Table detail

### 3.1 Header and facts

Identity, replication state pill, group and stream; below it the name mapping — `MFGDB.MFG.WORKORDERS → lakehouse.mfg_raw.workorders`. Then a six-card facts strip: **Source** (dialect + physical name), **Target** (dialect + physical name), **Rows in source** (estimate from the last refresh), **Changes today** (with time since last change), **Capture** (method + the supplemental-logging mechanism that method requires), **Apply latency** (p50, end to end).

### 3.2 Columns grid

One row per column: **#**, **Column** (source physical name), **Target column**, **Source type**, **Nullable**, **Key**, **Target type**, **Notes**, and the row actions.

- Types are rendered in each side's own vocabulary — a DB2 `VARCHAR(8)` lands as Databricks `STRING`, an Oracle `NUMBER(19)` as Snowflake `NUMBER(19,0)`, a Postgres `jsonb` as Snowflake `VARIANT`. The mapping is computed from an abstract column kind, so a dialect change re-renders the whole grid consistently.
- Key badges: `PK`, `UQ`, `IX`, or `—`.
- Notes carry the facts that decide behavior: `CDC watermark`, `LOB — captured out-of-band`, `masked on apply`, `FK → MFG.ROUTINGS`, and exclusions (`excluded — PII`, `excluded — PCI`), which render dimmed with `—` as their target type.

**Row actions.** **Edit** (all rows) and **Drop / Restore** (all rows except the primary key, which shows `key` instead — the apply matches rows on it and cannot lose it).

### 3.3 The column editor

One dialog, seven fields, because those are the fields that answer *what is this column, and what does it become*:

| Field | Notes |
| --- | --- |
| Column source name | Physical name in the source |
| Column target name | Physical name in the target — **independent of the source name in both directions** (`tables.md` §3.1) |
| Source type | Free text in the source dialect |
| Target type | Free text in the target dialect |
| Nullable | `NOT NULL` / `NULL` |
| Key | none / `PK` / `UQ` / `IX` |
| Notes | Free text; prefix with `!` to exclude the column from replication |

**Reset to source definition** discards every override on that column. Saving stores only the fields that actually differ from the catalogue definition, so reset is always exact and the resulting event names precisely what changed.

### 3.4 What a change ripples into

A column edit is not a cell update — it re-derives the screen:

- the columns grid (names, types, key badges, notes);
- **Keys and indexes** — PK, unique and index entries follow key-membership changes, and the target key line names the partition, cluster or sort column actually used;
- **Replication rules** — columns replicated *n* of *m*, renamed columns, excluded columns, dropped columns, restrict condition, key for apply, soft-delete behavior, actions in force, recent compare verdict;
- **both DDL panes** (below);
- an **event** in the ledger, plus a toast naming the consequence.

### 3.5 DDL — Source / Target

A two-tab pane rendering real DDL for the dialect on each side.

**Source** is what the catalogue holds, plus the statement capture requires — and that trailing statement is the point of showing it: Oracle `ADD SUPPLEMENTAL LOG GROUP … ALWAYS`, DB2 `DATA CAPTURE CHANGES INCLUDE LONGVAR COLUMNS`, SQL Server `sys.sp_cdc_enable_table`, PostgreSQL `REPLICA IDENTITY USING INDEX`. A table without it cannot produce before-images, so the operator sees it on the same screen as the structure.

**Target** is what the integrate job generates: kept columns only (excluded and dropped columns are absent), target names, target types, plus `OP_TYPE` and `OP_TS` added by the apply. Per platform: Snowflake `CREATE OR REPLACE TABLE … CLUSTER BY`, Databricks `USING DELTA` with `PARTITIONED BY (DATE(…))` and change data feed, S3 a Parquet message schema, PostgreSQL a table plus unique index.

**Partition, cluster and sort keys are chosen from surviving columns** — a timestamp or date index column where one exists, otherwise the primary key with no `DATE()` wrapper (Delta then omits `PARTITIONED BY` entirely). Dropping a column can never leave it named in the target DDL.

### 3.6 Compare and refresh history

Two panels — one per run type — showing only runs scoped to **this table**, running first. Each row states the outcome, duration and actor; clicking one opens that event in the ledger, expanded (see `run-history.md`). A table that has never been compared or refreshed says so.

### 3.7 Definition history

The per-table slice of the event ledger: what changed, when, and who did it.

## 3a. Removing a table — stop, then remove

Remove is a two-step, because removing a table is an operational stop and not a list edit.

1. **Arm.** The row's Remove button becomes **Confirm**.
2. **Stop dialog.** A dialog names the stream, the fully qualified source object and the target object, then offers the stop sequence:
   - *Drain in-flight changes* (default on) — let captured changes for this table finish applying; off discards them at the checkpoint.
   - *Drop the target table* (default off) — off leaves the target and its rows in place, the usual choice.
3. **Stop and remove.** Capture for that table ends at the next checkpoint — no other table in the stream is interrupted — a `STOP` event records every choice, and the registration goes.

Removal is scoped per stream (`stream·identity`), so removing a table from a duplicate leaves the original's registration intact, and the stream's registered-table count drops accordingly. Removals persist across reloads in `repl-removed-tables`.

A removed table reappears in the Add-table catalogue; registering it again is the standard add flow (`stream-ui.md`), and the initial load is a fresh refresh — or a repair-scope refresh if the target rows were kept. The flow is diagrammed in `Add Table Wireflow.dc.html` (remove sub-flow).

## 4. State and persistence

| State | Shape | Lifetime |
| --- | --- | --- |
| `colEdits` | `{ 'stream·table': { originalColumnName: { name?, tname?, type?, ttype?, nullable?, key?, note? } } }` | Session |
| `droppedCols` | `{ 'stream·table': { originalColumnName: true } }` | Session |
| `removedTables` | `{ 'stream·table': true }` | Persisted (`repl-removed-tables`) |
| `volUnits` | `{ streamId: 'Auto'\|'KB'\|'MB'\|'GB'\|'TB' }` | Persisted with user preferences |
| `tableSel` + `tableSelPipe` | Selected table, keyed by identity **and** stream | Session |
| `ddlView` | `'source'` \| `'target'` | Session |

**Selection and overrides are keyed by stream + table, not table name.** A duplicate registers the same source objects, so identity alone would open the original's detail and leak its column edits (`tkey(t)` builds the composite key).

Both override maps are keyed on the **original** column name, not the displayed one, so a rename never orphans a drop or an edit. The catalogue definition is never mutated — it is the baseline every reset returns to, which is also the product's position on the real system: the platform reads the source and writes the target, and owns neither name.

## 5. Deliberate omissions in the prototype

Add column, column reordering (before/after placement), the context preview toggle, drift check and adopt-from-actual, and the per-column settings provenance panel are specified in `tables.md` but not yet built here. Column changes are shown as staged plans in their toasts and events; the plan preview dialog itself is not implemented.
