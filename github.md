repo: TheBigOso/data_replicator
branch: main

## Last sync

date: 2026-07-26T20:30:00Z
commit: e97588e
note: Local project is the source of truth; changes are pushed from the downloaded project folder. GitHub access from this project is read-only.

### Updated in this project

- New connection wizard: five steps (location type, agent connection, location connection, capture/integrate, channel membership), required unique name, optional pipeline attachment, created connections persist into the list and detail screens.
- Hierarchy corrected: Connections, Jobs, and Events are virtual-fleet screens; Tables, Monitoring, and Admin are stream screens; each list scoped to the level opened from, with Global fleet console counts derived from the same data.
- Global fleet console: fleets and virtual fleets are selectable rows; enterability is grant-derived (SuperAdmin reaches everything).
- Browser Back/Forward walk the console via real history entries.
- Docs: `connections.md` gained the creation-wizard section and CON-10..14; `fleet-hierarchy.md` gained screen placement, navigation/history, and FLT-29..31; matrix at 173 criteria; README covers the wizard, hierarchy, permission model, and admin levels.

## Sync history

- 2026-07-26 — initial push (commit 8d74101) and README/connections spec push (commit e97588e).

## Screen map

| Screen | Built from |
| --- | --- |
| Replicator UI (all screens) | Authored in this project — `Replicator UI.dc.html`; specs in `uploads/repidata/Documents/` |
