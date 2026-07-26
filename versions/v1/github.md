repo: TheBigOso/data_replicator
branch: main

## Last sync

date: 2026-07-26T19:00:00Z
note: Local project is the source of truth; changes are pushed from the downloaded project folder. Read-only GitHub access from this project.

### Updated in this project

- Connections: sortable/filterable columns, per-user column chooser, per-row test; connection detail with agent/agentless, database connection, source/target properties, pipeline membership.
- Configuration dialogs: agent (host/port, cert pinning, credentials), Oracle database connection (ORACLE_HOME, local SID or TNS), capture/integrate method selection with configuration-time validation.
- Global fleet console: fleet rows read as selectable fleets; virtual fleet rows click through; SuperAdmin now reaches every fleet and virtual fleet (grant-derived, previously hardcoded).
- Real browser history — Back/Forward walk the console; seeded pipelines for generated division fleets so counts match the screens they open.
- Docs: new `connections.md` spec (CON-01..09); matrix at 165 criteria across 13 specs; README expanded with permission model, three admin levels, and prototype behaviors.

## Screen map

| Screen | Built from |
| --- | --- |
| Replicator UI (all screens) | Authored in this project — `Replicator UI.dc.html`; specs in `uploads/repidata/Documents/` |
