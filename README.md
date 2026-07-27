# data_replicator

Design and prototype work for an enterprise **CDC replication platform** — Rust capture and integrate agents, hub-routed encrypted file-log transport, log-based change capture from Oracle (direct redo, no LogMiner), SQL Server, PostgreSQL, and DB2 into Snowflake, Databricks, and file stores.

The product targets large regulated enterprises — defense, aerospace, manufacturing, finance — where air-gapped deployment, flat predictable licensing, and total documentation transparency decide the sale. It competes with Fivetran HVR, Oracle GoldenGate, and Qlik Replicate.

This repository is **design-stage**: it holds the design specifications and a working, browser-based prototype of the admin console. There is no product implementation, no build step, and no runtime dependency.

---

## Repository layout

| Path | What it is |
| --- | --- |
| `Replicator UI.dc.html` | The admin console prototype — every screen, fully interactive |
| `support.js` | Runtime that renders the prototype. No build step, no npm, no bundler |
| `uploads/repidata/Documents/` | The design specification set (see [Specifications](#specifications)) |
| `uploads/repidata/Documents/master-traceability-matrix.md` | The authoritative acceptance-criteria register |
| `uploads/repidata/Documents/diagrams/` | Wire diagrams, one per concept |
| `uploads/*.png` | Reference screenshots and wireframes gathered during design sessions |
| `CLAUDE.md` | Project conventions |
| `github.md` | Repo association and sync receipt |

## Running the prototype

Open `Replicator UI.dc.html` in a modern browser. Nothing to install.

Sign-in is by **email** — the product has no usernames anywhere. Test accounts:

| Account | Role | Sees |
| --- | --- | --- |
| `rn.reeves@corp.example` | SuperAdmin | Every enrolled fleet |
| `k.osei@corp.example` | Multi-system user | Only the fleets their grants reach (corp + rockets) |

Session state and per-user preferences — theme, sidebar width, table columns, sort order, pinned fleets — persist in browser storage and are isolated per account. Signing in as a different user gets that user's setup, not yours.

---

## Product principles

These are load-bearing; the prototype is designed to make each one visible rather than merely claimed.

**Enterprise flat license.** One price for the whole enterprise. No channel counting, no row metering, no usage telemetry. Perpetual license plus annual maintenance; the software never stops working if maintenance lapses.

**Nothing hidden.** All documentation — concepts, internals, file formats, wire protocol, troubleshooting — public, unpaywalled, and mirrorable into air-gapped enclaves. The product's own sharp edges are documented openly and converted into guardrails wherever possible.

**Air-gap native.** Signed offline license files, no phone-home, agent-initiated connection mode, offline docs bundle, AI features optional and offline-tolerant.

**The product proves itself.** The built-in compare feature verifies source-equals-target in CI after every test run — the same mechanism customers use to trust the product gates every merge.

---

## The console: what the prototype covers

### Hierarchy and navigation

Four levels — **Global Fleet → Fleet (hub server) → Virtual Fleet → Stream (pipeline)**. Each screen sits at the level that owns the objects it shows: the **virtual fleet** owns Connections, Jobs, and Events; each **stream** owns Tables, Monitoring, and Admin. Under a virtual fleet the sidebar lists its streams alphabetically, then Jobs, Events, and Connections. The sidebar is a searchable, expandable tree with a resizable width that persists per user, and it shows only what the signed-in operator's grants reach.

Screens: Global fleet console, Browse fleets, Fleet view, Virtual fleet overview, Pipelines list, Pipeline detail, Pipeline admin, Connections, Connection detail, New connection wizard, Tables, Table detail, Monitoring, Jobs, Events, and Admin at three levels (global, fleet, virtual fleet).

Every virtual-fleet screen is scoped by where it was opened from — from a stream it narrows to that stream, from the virtual fleet it covers all of them — and the counts published in the Global fleet console are derived from the same data those screens read, so a number you click matches what you land on.

### Identity and access

- Email is the sign-in identity and the unique user key; full name is separate and is what the console displays — in the user chip, the Users table, permissions rows, and grant dialogs.
- **Grant-scoped Global Fleet.** The cross-hub-server view HVR never had, gated by a `FleetViewer` capability. Operators see only the systems their grants reach; the console states plainly how many enrolled systems exist beyond their view rather than pretending they do not.
- **Fleet browse page** listing accessible fleets, with star-to-pin. Pinning and unpinning updates the sidebar immediately, and the sidebar filters pinned fleets against current grants — a revoked grant removes the fleet, not just its data.
- Environment colour per fleet (production, test, and so on), carried into the accent colour so an operator can tell at a glance which environment they are acting in.

### The permission model

Access is granted, never assumed. A grant pairs a **permission** with a **scope** — either the repository (company-wide) or a single virtual fleet — and a user's effective access is the union of their grants. `All Users` carries a repository-level `ReadOnly` grant, so newly created users inherit view-only access by default and nothing more.

**Repository scope** — company-wide permissions:

| Permission | Grants |
| --- | --- |
| `SuperAdmin` | Everything, everywhere — every fleet and virtual fleet, all admin levels, user management. Implies every other permission, including `FleetViewer`. Grantable only by another SuperAdmin |
| `SysAdmin` | Full access to the system, including all hubs and managing users |
| `HubCreation` | Create new hubs; implies `HubOwner` on the hubs it creates |
| `ReadStatistics` | Read fleet-wide statistics, sizing data, and sync reports — there is no metered usage to read, by design |
| `FleetViewer` | See the Global fleet console — every hub server and virtual fleet in the company, read-only |

**Virtual fleet scope** — permissions granted on one virtual fleet at a time:

| Permission | Grants |
| --- | --- |
| `HubOwner` | Full control of the current hub, including changing access and properties |
| `ReadWrite` | Define and change objects in the current hub |
| `ReadExecRefresh` | Perform refresh and compare, start/stop jobs, and view objects in the current hub |
| `ReadExec` | Perform compare, start/stop jobs, and view objects in the current hub |
| `ReadOnly` | Only view objects in the current hub |

Two properties of the model are deliberate and visible in the console:

**Sight and touch are separate.** `FleetViewer` grants sight, not touch: hubs where an operator's access is "none" remain read-only summaries in the Global fleet console. Operating requires switching into a fleet, which requires a grant on it. Systems an operator holds no grant on are hidden entirely, and the console says how many exist rather than pretending the fleet is smaller than it is.

**Admin authority is bounded by level.** Global Fleet Admin manages every grant, repository-wide and per virtual fleet. Fleet Admin manages grants on its own fleet's virtual fleets and sees repository-wide grants read-only. Virtual Fleet Admin manages grants on that one virtual fleet only. A SuperAdmin can manage every grant from any admin screen — but cannot revoke their own SuperAdmin grant; only another SuperAdmin can.

### The three admin levels

Admin is not one screen with permission checks sprinkled through it — it is the *same* screen bounded by where the operator stands in the hierarchy. Each level sees the objects it owns and reads the levels above it without being able to change them, so authority is legible from the screen itself rather than discovered by clicking and being refused.

| | **Global Fleet Admin** | **Fleet Admin** | **Virtual Fleet Admin** |
| --- | --- | --- | --- |
| Scope | The whole repository — every fleet, every virtual fleet | One fleet (hub server) and the virtual fleets inside it | One virtual fleet |
| Reached from | Global fleet console → Global Admin | A fleet → Fleet Admin | A virtual fleet → VF Admin |
| Held by | `SuperAdmin`, `SysAdmin` | `HubOwner` on a fleet | `HubOwner` on a virtual fleet |
| Users | Create, edit, disable users; set full name, email, and auth method | View users; grant on this fleet's virtual fleets | View users; grant on this virtual fleet |
| Grants it can edit | Repository-wide **and** any virtual fleet | This fleet's virtual fleets — repository-wide grants are read-only | This virtual fleet only — everything else read-only |
| Fleets | Enroll a new fleet, set environment (production/test/…) | Properties of this fleet; enroll virtual fleets into it | — |
| Repository settings | Yes — auth methods, retention, gather cycle | Read-only | Read-only |
| Snapshots and exports | Whole repository | This fleet | This virtual fleet |

The console states the operator's own boundary on the Permissions tab in plain words — for example *"Fleet Admin · hubsrv-corp — you can manage grants on this fleet's virtual fleets; repository-wide grants are read-only"* — so nobody has to infer their authority from which buttons are greyed.

Two consequences worth knowing:

- **A Fleet Admin cannot widen their own reach.** Repository-scope permissions (`SuperAdmin`, `SysAdmin`, `HubCreation`, `ReadStatistics`, `FleetViewer`) are only grantable from Global Fleet Admin, so a fleet-level owner cannot grant themselves company-wide sight or hub-creation rights.
- **Global Fleet Admin is where fleets come into existence.** Enrolling a fleet and setting its environment colour are global acts, because a new fleet changes what every `FleetViewer` sees.

### Connections — specified in full in [`connections.md`](uploads/repidata/Documents/connections.md)

The most developed area of the prototype, on the premise that connection problems are the most common cause of a stalled pipeline.

**The list** shows Connection (with a source/target role pill), Platform, Description, Agent, Heartbeat, and Status, plus a per-row connectivity test. Available through a **column chooser**: host/endpoint, created date, created by, pipeline count, and last test result. The Test action is itself hideable; the Connection column is locked on.

Every visible header sorts (click to reverse, with a visible indicator; default **Connection descending**), and numeric columns sort numerically — a 14-minute-stale agent must not sort between 1s and 2s. Every visible header carries a filter box; filters combine and produce an explicit empty state. **Column visibility and sort order persist per user**; filters are session-only.

**Connection detail** answers "what breaks if this is down" on the same page as the configuration: agent card (agent-based with binary, host, port, and heartbeat, or agentless hub-direct), database connection card, resolved source/target properties, and **pipeline membership** — every pipeline using the connection, the role it plays there, table count, and daily volume, each linking through to the pipeline.

**Three configuration dialogs**, sharing one contract — trade-offs stated inline, choices constrained by the class capability matrix, and a *Test connection before saving* checkbox that is on by default but can be unchecked (the confirmation discloses which happened, and every save lands in the event ledger):

- **Agent** — agent vs agentless mode with each mode's cost stated, agent host and port, test agent connection (reachability, latency, mTLS handshake, certificate, hub/agent version match), configure agent service, pinned public certificate with fingerprint plus rotate-certificate and re-issue-enrollment-token actions, and agent credentials.
- **Database connection** — for Oracle: `ORACLE_HOME` and a connect path of either local connect with a **SID** (requires the agent on the Oracle host) or **Oracle TNS** (a `tnsnames.ora` name or the `[//]HOST[:PORT]/SERVICE_NAME` form, which re-derives host, port, and service across the console). Host, port, and database for other platforms. Credentials are vaulted on the hub, never written to agent disk or logs.
- **Source and target properties** — Oracle capture method (**direct redo** or **archived-log only**), pluggable-database and SAP-source options, and advanced capture properties (extra redo archive directory, invisible columns, intermediate staging directory, case-sensitive names). PostgreSQL logical slot with slot and publication. Log readers for SQL Server and DB2. Target integrate method: continuous, batched cycles, or burst apply, with automatic state tables. Choosing direct redo over a non-loopback TNS connection raises a **configuration-time warning** — the misconfiguration that otherwise surfaces as a runtime capture failure.

### Pipelines, tables, and operations

Pipeline list and detail with replication status, latency, and volume; per-pipeline Tables with the verified-status model; Monitoring with alerts surfaced as sidebar badges; Jobs; and the Events ledger. Admin exists at global, fleet, and virtual-fleet level with capability-gated create, edit, and delete.

**Tables and table structure** — specified in full in [`tables-ui.md`](uploads/repidata/Documents/tables-ui.md). The Tables list covers every table across every pipeline (identity, pipeline, name in source, group, recent refresh, recent compare, change sparkline). Clicking a table name opens **table detail**: a facts strip (dialect per side, row estimate, changes today, capture method and the supplemental logging it requires, apply latency), the **columns grid** — source name, target name, source type, nullability, key, mapped target type, notes — keys and indexes, replication rules, a **Source / Target DDL** pane rendering real dialect-correct DDL, and definition history.

Columns are editable per row: source name, target name, both types, nullability, key membership, and notes. **Source and target column names are independent in both directions** — renaming one side never moves the other, because both hang off a column identity rather than off each other (`tables.md` §3.1). Columns can be dropped and restored; the primary key cannot be dropped. Every change re-derives the grid, the rules panel, and both DDL panes, and lands in the event ledger.

Destructive and structural actions are modelled as **plans**: the console states what would happen — jobs draining at checkpoints, file-log frames retained until acknowledged, target left untouched — before anything is confirmed.

---

### Prototype behaviors worth knowing

These are properties of the console as built, not aspirations — they are what an operator actually experiences when clicking through:

- **Real browser history.** Every screen change pushes a history entry, so Back and Forward walk the console (fleet → virtual fleet → pipeline → connection) instead of leaving the page. Modals, filter keystrokes, and toasts deliberately create no entries — Back should not undo typing.
- **Grant-derived everything.** Visibility, enterability, and access labels all come from the operator's grants rather than being hardcoded per screen: a SuperAdmin can enter every virtual fleet in every fleet; a non-super sees `none` on ungranted ones and is told which grant to ask for.
- **Per-user, per-account persistence.** Theme, sidebar width, pinned fleets, connection column sets, and sort order are stored per signed-in account and restored at sign-in. Filters are session-only, being an act of looking rather than a preference.
- **Environment signalling.** Each fleet carries an environment (production, test, …) whose colour becomes the console accent, so the operator can see which environment they are acting in without reading a label.
- **Honest empty states.** Screens with nothing to show say so — no connections match the filters, no pipelines defined in this virtual fleet, this connection belongs to no pipeline — rather than rendering a blank area that reads as a loading failure. Counts shown in one screen match what the next screen contains.
- **Nothing silently succeeds.** Every save, test, switch, and structural action reports what happened, including whether a connection was tested before saving, and says when it would be recorded in the event ledger.

---

## Specifications

Each specification carries a phased test plan, test procedures, and numbered acceptance criteria feeding the master traceability matrix.

| Document | Subject |
| --- | --- |
| `architecture.md` | Hub-routed core, repository, REST API, file-log transport |
| `agent.md` | Rust agent: enrollment, mTLS, static binary, upgrade rings |
| `location.md` | Location model, capability matrix, credential envelope, configuration-time validation |
| `connections.md` | The operator-facing connection surface — list, detail, dialogs, testing |
| `channel.md` | What to replicate: table selection, identity derivation, mappings |
| `tables.md` | Fleet-wide table surface, verified status (including honest INCONCLUSIVE), drift check, per-side column names |
| `tables-ui.md` | The console surface for tables: list, table detail, columns grid, column editor, DDL panes |
| `replication-topologies.md` | Broadcast, consolidation, cascade; the topology view |
| `scheduler.md` | Continuous CDC, scheduled refresh, scheduled compare |
| `refresh.md` | Online refresh without suspending integrate |
| `compare.md` | Source-equals-target verification, multi-target verdicts |
| `slicing-design.md` | Slice types, parallel writers, throughput |
| `jobs.md` | Job model, priority classes, resource caps |
| `events.md` | Audit ledger: completeness by construction, immutability, SIEM forwarding |
| `fleet-hierarchy.md` | The four-level hierarchy, Global Fleet console, admin and grant model |
| `sizing.md` | Environment sizing: storage inventory, compute distribution, quota formulas |
| `naming.md`, `filesystem-layout.md` | Naming rules and on-disk layout |
| `master-traceability-matrix.md` | Consolidated criteria, procedures, state, evidence |

### How verification works

Every specification follows the same four-link chain, and a concept is only firm when all four exist: **design** (with worked examples wherever behavior could surprise), **test plan** (phases with entry and exit conditions), **test procedures** (executable by anyone, not dependent on the author's memory), and **acceptance criteria** (numbered pass/fail rows).

The working rule: **a criterion is checked off only when its procedure has been executed, every expected result observed, and the listed evidence archived.** No procedure, no pass. Evidence lives with the release record so any pass can be re-audited later.

Current state of the matrix: **165 criteria across 13 specifications**, none yet run — this is a design repository.

---

## v1 scope

**Committed.** Hub-routed core (agents, encrypted file log, REST API, scheduler, repository); continuous CDC, scheduled refresh, and scheduled compare; PostgreSQL source and the PostgreSQL-to-PostgreSQL lab pipeline as the verification baseline.

**In design for v1.** Oracle source via direct redo without LogMiner; SQL Server source; DB2 source; Snowflake and Databricks targets; file targets (S3-compatible, ADLS, local).

**Deferred.** Kafka target, active/active bidirectional and n-way replication, hub high availability, peer-to-peer routing, AIX/Solaris agents. The platform is a replication product, not a general-purpose ETL or cloud-managed integration service.

---

## Status and caveats

Design-stage prototype. It models real product behavior, constraints, and permission gating, but it does not connect to a hub, an agent, or a database. Actions that would mutate a real fleet report what they would do instead of doing it.

Note: `uploads/repidata/Replicator UI.dc.html` is a stale earlier copy of the prototype. The current one is `Replicator UI.dc.html` at the repository root.
