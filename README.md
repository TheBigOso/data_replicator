# data_replicator

Design and prototype work for an enterprise **CDC replication platform** — Rust agents, hub-routed transport, competing with HVR, GoldenGate, and Qlik Replicate.

This repository holds the product's design specifications and a working, browser-based UI prototype of the admin console. There is no build step and no runtime dependency: open the prototype file in a browser.

## Contents

| Path | What it is |
| --- | --- |
| `Replicator UI.dc.html` | The admin console prototype — all screens, fully interactive |
| `support.js` | Runtime that renders the prototype (no build step, no npm) |
| `uploads/repidata/Documents/` | Design specifications and the acceptance-criteria traceability matrix |
| `CLAUDE.md` | Project conventions |
| `github.md` | Repo association and sync receipt |

## Running the prototype

Open `Replicator UI.dc.html` in a modern browser. Nothing to install.

Test accounts (sign-in is by email; no usernames anywhere in the product):

- `rn.reeves@corp.example` — SuperAdmin; sees every fleet
- `k.osei@corp.example` — multi-system user; sees only granted fleets

Session and per-user preferences (theme, sidebar width, table columns, sort order) persist in browser storage and are isolated per account.

## What the prototype covers

**Identity and access**
- Email-based sign-in; full name is the identity shown throughout the console
- Grant-scoped Global Fleet view — you see only the fleets your grants reach
- Fleet browse page with star-to-pin, keeping the sidebar in sync with your grants

**Connections**
- Sortable and filterable on every column, with a per-user column chooser (host/endpoint, created date, created by, pipeline count, last test result) and a per-row connectivity test
- Connection detail: agent-based vs agentless, database connection, source/target properties, pipeline membership

**Connection configuration**
- *Agent*: agent vs agentless mode, agent host and port, pinned public certificate with rotation and enrollment-token re-issue, agent credentials, save-without-testing
- *Database connection*: Oracle `ORACLE_HOME` with local-SID or TNS connect; host/port/database for other platforms; credentials vaulted on the hub
- *Source and target properties*: platform-aware capture methods (Oracle direct redo vs archived-log only, PostgreSQL logical slot, log readers), pluggable-database and SAP options, advanced capture properties, and target integrate methods (continuous, batched, burst)

## Design specifications

Specs live in `uploads/repidata/Documents/`. Every design decision carries a numbered acceptance criterion, tracked in `master-traceability-matrix.md` — read the relevant spec before changing UI behavior.

## Status

Design-stage prototype. It models real product behavior and constraints, but does not connect to a hub, an agent, or a database; actions that would mutate a real fleet report what they would do.
