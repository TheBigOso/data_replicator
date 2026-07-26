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

Four levels — **Global Fleet → Fleet (hub server) → Virtual Fleet → Pipeline** — with pipeline-scoped sections beneath each pipeline (Connections, Tables, Monitoring, Jobs, Events, Admin). The sidebar is a searchable, expandable tree with a resizable width that persists per user, and it shows only what the signed-in operator's grants reach.

Screens: Fleet overview, Browse fleets, Global fleet console, Fleet view, Pipelines list, Pipeline detail, Pipeline admin, Connections, Connection detail, Tables, Monitoring, Jobs, Events, and Admin at three levels (global, fleet, virtual fleet).

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

Destructive and structural actions are modelled as **plans**: the console states what would happen — jobs draining at checkpoints, file-log frames retained until acknowledged, target left untouched — before anything is confirmed.

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
| `tables.md` | Fleet-wide table surface, verified status (including honest INCONCLUSIVE), drift check |
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
