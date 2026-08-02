repo: TheBigOso/data_replicator
branch: main

## Last sync

date: 2026-08-02T00:00:00Z
note: Local project is the source of truth; changes are pushed from the downloaded project folder. GitHub access from this project is read-only. Commit sha unknown until the next push — this entry receipts the local state to be pushed.

### Updated in this project

- Terminology locked to **Stream** everywhere: channel/pipeline/orca swept from all specs, the prototype UI, and every wireflow (HVR parity-matrix left columns exempt); `channel.md` → `stream.md` (CHA-xx → STR-xx).
- Doc set restructured: `location.md` + `connections.md` merged into `connection.md`; `add-table-ui.md` + `streams-duplicate.md` folded into new `stream-ui.md`; `hvr-paste.txt` and 155 pasted screenshots deleted.
- New specs: `fleet-ui.md`, `virtual-fleet-ui.md`, `jobs-ui.md`, `events-ui.md`, `stream-ui.md`, `fleet-paths.md` (the console tree on disk); `timeline.md` rewritten to four scopes; `architecture.md` gained §2.2 (console application architecture + the navigation tree).
- Wireflows: new Fleet, Virtual Fleet, Stream, Connections, Jobs, Events, VF Timeline wireflows; all 16 foldered by hierarchy level (global-fleet/ · fleet/ · fleet/virtual-fleet/ · …/connections/ · …/streams/) with surface specs moved beside them and MAP/CANONICAL scope strips added.
- Prototype: severity + date-range + search filters and a 90-day history on global triage; jobs upgrades (visible state machine, MISSING reconciliation, bulk actions with blast radius, timeline links); fleets renamed TITAN/PHOENIX/ATLAS/SUMMIT/DEV; VF ids now orca-*.
- Traceability matrix: +103 console-surface and path-model rows (GFC, FLC, VFC, JBS, EVU, STU, TML, HPT), counts recomputed (276 total).

## Sync history

- 2026-08-01 — stream rename, doc restructure, wireflow foldering, matrix expansion (pending push).
- 2026-07-26 — tables fixture, table detail screen, column editing (pending push).
- 2026-07-26 — initial push (commit 8d74101) and README/connections spec push (commit e97588e).

## Screen map

| Screen | Built from |
| --- | --- |
| Replicator UI (all screens) | Authored in this project — `uploads/repidata/Replicator UI.dc.html`; model specs in `uploads/repidata/Documents/`, surface specs beside their wireflows |
| Global Fleet console, Global Admin, Users/Permissions | `uploads/repidata/global-fleet/` (specs + wireflows) |
| Fleet page | `uploads/repidata/fleet/` |
| VF page, Jobs, Events, VF Timeline, Alert Rules, run history | `uploads/repidata/fleet/virtual-fleet/` |
| Connections | `uploads/repidata/fleet/virtual-fleet/connections/` |
| Stream page, New stream, Activation, Compare, Tables, Add table | `uploads/repidata/fleet/virtual-fleet/streams/` |
