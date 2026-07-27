repo: TheBigOso/data_replicator
branch: main

## Last sync

date: 2026-07-26T22:05:00Z
commit: e97588e
note: Local project is the source of truth; changes are pushed from the downloaded project folder. GitHub access from this project is read-only.

### Updated in this project

- Tables: 39 tables across seven pipelines and eight groups (new IOT group), replacing the 10-row fixture.
- Table detail screen, opened by clicking a table name: facts strip, columns grid (source name, target name, source/target types, nullability, key, notes), keys and indexes, replication rules, Source/Target DDL panes with dialect-correct capture statements, definition history.
- Column editing: per-row Edit dialog (both names, both types, nullable, key, notes) and Drop/Restore; source and target column names are independent in both directions; PK cannot be dropped; every change re-derives the DDL and writes a DEFINITION CHANGE event.
- Docs: `tables.md` gained §3.1 (per-side column names) and TBL-06; new `tables-ui.md` specifies the console surface; README updated.

## Sync history

- 2026-07-26 — tables fixture, table detail screen, column editing (pending push).
- 2026-07-26 — initial push (commit 8d74101) and README/connections spec push (commit e97588e).

## Screen map

| Screen | Built from |
| --- | --- |
| Replicator UI (all screens) | Authored in this project — `Replicator UI.dc.html`; specs in `uploads/repidata/Documents/` |
| Tables, Table detail | `Replicator UI.dc.html`; specs `uploads/repidata/Documents/tables.md`, `tables-ui.md` |
