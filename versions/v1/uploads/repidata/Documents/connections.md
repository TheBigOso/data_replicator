# Connections — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** UI concept and design specification
**Status:** v1 design; prototyped in `Replicator UI.dc.html`
**Related:** `location.md` (the underlying location model, capability matrix, credential handling), `agent.md`, `channel.md`, `fleet-hierarchy.md`

---

## 1. Purpose and Positioning

A **connection** is the console's presentation of a location: the databases and stores a fleet replicates between, with the agent (or agentless path) that reaches each one. `location.md` defines the model — classes, capability matrix, credential envelope, configuration-time validation. This document defines the operator-facing surface: how connections are listed, inspected, configured, and tested, and what an operator can determine without leaving the screen.

The design premise is that connection problems are the most common cause of a stalled pipeline, so the console must answer three questions in one view: **is it reachable, what is it, and what breaks if it's down.** The list answers the first two; the detail screen answers the third by showing pipeline membership on the same page as the connection's configuration.

## 2. Connections List

The list is a table, not a card grid: operators compare connections against each other (which agent version, which is stale, which has no pipelines) and comparison demands aligned columns.

### 2.1 Columns

Shown by default:

| Column | Content |
|---|---|
| Connection | Name in monospace, with a `source` / `target` role pill; the name links to the connection detail screen |
| Platform | Class and capture/apply mechanism, e.g. `Oracle 19c · direct redo`, `PostgreSQL 17 · logical` |
| Description | Operator-written purpose — what business system this is |
| Agent | Agent binary version and platform, or `agentless · hub-direct` |
| Heartbeat | Time since the last agent heartbeat (or hub reachability probe when agentless), relative |
| Status | `Healthy` / `Unreachable` pill derived from the heartbeat and last validation result |
| Test | Per-row button running the connectivity test (§5) |

Available through the column chooser, hidden by default:

| Column | Content |
|---|---|
| Host / endpoint | Resolved host and port, or the store URI |
| Created | Date the connection was defined |
| Created by | Full name of the user who defined it |
| Pipelines | Count of pipelines using this connection |
| Last test | Outcome and age of the most recent connectivity test |

The Test button is itself a hideable column — operators who never test from the list can reclaim the space. The Connection column is locked on; hiding the identifier is never useful.

### 2.2 Sorting and filtering

Every visible header is a sort control: click to sort, click again to reverse, with a `▲`/`▼` indicator on the active column. Numeric columns (Heartbeat, Pipelines) sort numerically, not lexically — a 14-minute-stale agent must not sort between 1s and 2s because "1" precedes "2". The default order is **Connection descending**, with the indicator visible on load so the sort state is never implicit.

Each visible column carries a filter box under its header. Filters are substring matches, combine across columns (AND), and are reflected immediately; when nothing matches, the table shows an explicit empty state rather than an ambiguous blank area. The Connection filter also matches the role, so `target` narrows to targets without a separate control.

### 2.3 Persistence and scoping

Column visibility and sort order are **per user**, stored with the operator's other workspace preferences and restored at sign-in; two operators sharing a fleet keep their own table setups. Filters are session-only — they are a transient act of looking, not a preference.

Opened from a pipeline, the list is scoped to that pipeline's source and target. Opened at the virtual-fleet level it shows every connection the operator's grants reach.

## 3. Connection Detail

The detail screen is organized as three configuration cards plus a membership table, so an operator can read the whole connection without scrolling through a form.

**Header** — name, role pill, status pill, platform and description, and a **Test connection** action.

**Agent card** — for agent-based connections: mode, agent binary, enrollment method, agent host, agent port, and heartbeat age. For agentless connections: a plain statement that the hub connects directly, with the reachability probe age. Each card has an Edit action opening the corresponding dialog (§4).

**Database connection card** — host, port, database, and user; for Oracle also `ORACLE_HOME` and the connect path (`Local · SID x` or `TNS · x`). A standing note states that credentials are vaulted on the hub and never written to agent disk or logs — the credential-handling promise from `location.md` restated where the operator can act on it.

**Source and target properties card** — the resolved capture or integrate method plus the enabled options, so the effective configuration is visible without opening the editor.

**Pipeline membership** — one row per pipeline using this connection: pipeline name (linking to the pipeline), replication status, the role the connection plays *in that pipeline*, table count, and average daily volume. This is the blast-radius answer: an operator looking at an unreachable connection sees immediately which pipelines are affected. An **Add to an existing pipeline** action starts the membership change; a connection with no pipelines shows an explicit empty state rather than an empty table.

## 4. Configuration Dialogs

All three dialogs share one contract: they state the trade-off of each choice inline, they validate against the class capability matrix rather than accepting anything and failing at runtime, and they carry a **Test connection before saving** checkbox that is checked by default and can be unchecked. Saving untested is legitimate — an operator configuring a database that is down for maintenance must be able to record the configuration — so the product allows it, says so in the confirmation, and defers validation to the next heartbeat or capability check. Every save is recorded in the event ledger.

### 4.1 Agent dialog

Two mutually exclusive modes, presented as cards with their trade-offs stated rather than as a bare toggle:

- **Connect via agent** — an enrolled binary on or near the database host, over mTLS. Reduces network cost, distributes CPU load, and enables capture directly from the database logging system.
- **Agentless** — the hub connects to the endpoint itself. Simpler and zero-footprint; all capture load and network cost land on the hub.

In agent mode the dialog exposes **agent host** and **agent port**, a **Test agent connection** action (reachability, latency, mTLS handshake, certificate verification, and a hub/agent version match check), and a **Configure agent service** action for service account, spool directory, log level, and upgrade ring.

A certificate panel states that the agent's public certificate is pinned, shows its fingerprint, and offers two actions: **rotate certificate** (the agent picks up the new pinned certificate on its next heartbeat; the old certificate is honored for a grace period) and **re-issue enrollment token** (single-use, short-lived, recorded in the ledger). Agent user and password complete the section.

Switching a connection to agentless is a visible change, not a silent one: the Agent column in the list and the detail card both re-render to `agentless · hub-direct`.

### 4.2 Database connection dialog

Platform-shaped rather than generic. For **Oracle**:

- `ORACLE_HOME`
- A connect-path choice: **Local connect to database** with a **SID** — which requires the agent to run on the Oracle host itself — or **Oracle TNS**, connecting over SQL*Net using either a name defined in `tnsnames.ora` or the `[//]HOST[:PORT]/SERVICE_NAME` form. Saving a TNS string re-derives host, port, and service for display everywhere else in the console.

For other platforms: host, port, and database. Both variants take the database **user** and **password**, with the vaulting statement repeated at the point of entry.

### 4.3 Source and target properties dialog

Method selection is the primary control and is filtered to what the class actually supports.

**Oracle sources** — capture method: **Direct redo** (reads online redo and archive logs directly, no LogMiner; lowest latency, requires log access on the Oracle host) or **Archived-log only** (reads archived logs as they close; no online redo access needed, latency bounded by the log switch interval).

The dialog cross-validates against the database connection: choosing Direct redo while the connection is TNS raises an inline warning that direct redo only works if the TNS connection is loopback — the agent running on Oracle's own machine — or if a local SID connection is used. This is the class of misconfiguration that otherwise surfaces as a runtime capture failure, caught at configuration time as `location.md` requires.

Oracle options: **Pluggable database** (capture from a PDB requires root-container access) and **SAP source** (reads SAP dictionary metadata during table selection; required to unpack cluster and pool tables). Under **Advanced capture properties**, collapsed by default: extra redo archive directory with path, show invisible columns, intermediate staging directory with path, and case-sensitive names.

**PostgreSQL sources** — logical replication slot, with slot and publication names.

**SQL Server and DB2 sources** — transaction log reader and `db2ReadLog` respectively.

**Targets** — default integrate method: **Continuous** (apply each change as it arrives; lowest latency), **Batched cycles** (accumulate and apply on a cycle; fewer target commits), or **Burst apply** (coalesce into set-based operations; best for warehouse targets). The value is a default that a pipeline may override. Options: create state tables automatically (exactly-once apply state) and case-sensitive names.

## 5. Connectivity Testing

One test action is reachable from three places — the list row, the detail header, and each dialog — and reports the same shape of result: on success, latency plus what was verified (mTLS handshake, certificate, version match, capability matrix); on failure, the specific cause and the remediation direction, e.g. an unreachable agent naming how long it has been unreachable and pointing at enrollment and network path. Consistent with `location.md`, a failure never dead-ends in "contact support".

## 6. HVR Parity Matrix

| HVR concept | This platform | Delta |
|---|---|---|
| Location list | Connections list | Sortable and filterable on every column; per-user column sets |
| Location properties dialog | Platform-shaped connection dialogs | Choices constrained by the capability matrix; trade-offs stated inline |
| Oracle ORACLE_HOME + local/TNS connect | Same | TNS string re-derives host/port/service for display |
| Capture method selection | Same | Cross-validated against the connect path at configuration time |
| Agent vs agentless | Same | Cost/benefit of each mode stated in the dialog; switching is visible in the list |
| Test connection | Same, from list, detail, and dialogs | Save-without-test explicitly supported and disclosed |
| — | Pipeline membership on the connection | Blast radius visible where the failure is diagnosed |

## 7. Test Plan

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Table behavior | CON-01, CON-02, CON-03 | Playwright against seeded fleet fixtures | Connections list implemented | Sort, filter, and per-user column persistence proven across two accounts |
| B | Configuration dialogs | CON-04, CON-05, CON-06, CON-07 | Misconfiguration fixture set from `location.md` | Phase A exit; dialogs implemented | Every fixture caught at configuration time with documented remediation |
| C | Testing and disclosure | CON-08, CON-09 | Integration lab incl. a deliberately unreachable agent | Phase B exit | Test results and save-without-test disclosure verified; ledger entries present |

### 7.1 Methods

Table behavior is driven by Playwright against seeded fixtures, including a fixture whose heartbeat ages are chosen to fail a lexical sort (1s, 2s, 14m) — the numeric-sort criterion is unfalsifiable without it. Per-user persistence is proven by configuring distinct column sets on two accounts, reloading, and asserting neither leaked into the other.

Dialog validation reuses the misconfiguration fixture set: for connections, the decisive fixture is an Oracle location reachable only over non-loopback TNS with Direct redo requested — the warning must appear at configuration time, before any job runs.

## 8. Acceptance Criteria

| ID | Criterion |
|---|---|
| CON-01 | The connections list shows Connection (with source/target role), Platform, Description, Agent, Heartbeat, and Status, plus a per-row test action that reports pass with latency or fail with cause |
| CON-02 | Every visible column is sortable, toggling ascending/descending with a visible indicator; the default order is Connection descending with the indicator shown on load; Heartbeat and Pipelines sort numerically |
| CON-03 | Per-column filter boxes combine across columns and show an explicit empty state; column visibility and sort order persist per user across sessions and never leak between users |
| CON-04 | The column chooser adds and removes columns including Host/endpoint, Created, Created by, Pipelines, and Last test; the Test action is hideable; the Connection column cannot be hidden |
| CON-05 | Connection detail shows agent mode (agent-based with host, port, binary, and heartbeat, or agentless), database connection, resolved source/target properties, and pipeline membership with the role played in each pipeline |
| CON-06 | The agent dialog switches between agent and agentless, exposes agent host and port, tests the agent (reachability, latency, mTLS, certificate, version match), and supports certificate rotation and single-use enrollment token re-issue |
| CON-07 | The Oracle database dialog exposes ORACLE_HOME and a local-SID or TNS connect path; a saved TNS string re-derives host, port, and service consistently across the console |
| CON-08 | Capture and integrate method choices are constrained to what the class supports, and Direct redo requested over a non-loopback TNS connection raises a configuration-time warning naming the loopback or local-SID requirement |
| CON-09 | Every configuration dialog defaults to testing before saving, allows saving untested, discloses in the confirmation which of the two occurred, and records the save in the event ledger |
