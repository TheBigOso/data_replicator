# Connection — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification — the model and its console surface
**Status:** v1 design; prototyped in `Replicator UI.dc.html`, wireflow in `Connections Wireflow.dc.html`. Connector-specific requirements live with each connector
**Related:** `agent.md`, `stream.md`, `fleet-hierarchy.md`, `virtual-fleet-ui.md`, `scheduler.md`
**History:** merged from `location.md` and `connections.md` (2026-08-01), completing the location → connection rename in `naming.md` §3. **LOC-xx criterion ids are retained unchanged** — the traceability matrix's first rule is that ids stay stable — so LOC covers the model and CON covers the surface, in one document.

---

## 1. Purpose and Positioning

A **connection** is a storage endpoint the platform captures changes from (source) or integrates changes into (target): a database, or a file store. Connections are defined once, centrally, in the repository, and referenced by any number of streams — connection details, credentials, and reachability are connection concerns; what to replicate is a stream concern. This mirrors the HVR *location* concept while tightening the parts HVR leaves loose: capability discovery, credential handling, and configuration-time validation.

The console surface follows from one observation: **connection problems are the most common cause of a stalled stream**, so the screens must answer three questions in one view — **is it reachable, what is it, and what breaks if it's down.** The list answers the first two; the detail screen answers the third by showing stream membership on the same page as the configuration.

Sections 2–5 define the model. Sections 6–10 define the surface.

## 2. The Connection Model

Every connection carries: a unique name (fully qualified naming supported so `PROD.ERP01` and `TEST.ERP01` coexist unambiguously); a class (Oracle, PostgreSQL, SQL Server, DB2 LUW, Snowflake, Databricks, Kafka, S3/ADLS, ...); connection properties (host, port, service/database, cloud stage details); a reachability method (which agent serves it, or agentless); credentials (see section 5); and role eligibility (source, target, or both — derived from the class capability matrix, not asserted by the user).

### 2.1 Connection classes and the capability matrix

Each class declares, in machine-readable form, exactly what it supports: capture methods available (log-based, scheduled-refresh-only), integrate methods (burst, continuous), refresh/compare support, slicing types available, data type mappings, and version ranges. The published capability matrix (transparency principle) is generated from these declarations, so documentation and enforcement share one source of truth. The UI constrains choices to what the class actually supports at configuration time rather than failing at job runtime.

Scheduled-refresh-only sources deserve emphasis: any database reachable by SELECT with a read-only account can be a source connection in refresh mode (see Scheduler and Refresh Modes). This expands the source universe far beyond the log-based connector list and gives sales a soft landing — start with SELECT-only privileges, upgrade the connection to CDC when access matures.

## 3. Reachability: Agent and Agentless

A connection is reached either through a named agent (the normal case — the agent co-located with or near the data store performs the heavy work) or agentlessly, where the hub or a designated agent connects directly over the DBMS protocol: PostgreSQL wire protocol with logical replication, Oracle SQL*Net including BFILE access to redo/archive files (the path that covers Amazon RDS for Oracle and hosts where no agent may be installed). Agentless trades performance and offload for zero-footprint access; the choice is per connection and the trade-off is documented per class.

## 4. Configuration-Time Validation

Creating or editing a connection runs a validation suite immediately: connectivity, authentication, privilege sufficiency for the intended role (e.g., supplemental logging grantable, replication slot creatable, stage writable), and version support. Results are stored and displayed on the Connections screen with a health state (reachable, degraded, failing) refreshed by lightweight periodic probes. Every failure links to a public documentation page naming the missing privilege and the exact grant statement — no "contact support" dead ends.

## 5. Credential Handling

Credentials are stored in the repository under envelope encryption; plaintext never appears in logs, API responses, exports, or the UI after entry. Where the customer runs a secrets manager, a connection may reference an external secret (vault path) instead of storing material at all — the serving agent resolves it at connect time. Rotation is supported without stream restart: the next connection attempt uses the new material. Service-account philosophy per class is documented (least privilege, read-only where the mode allows it), with copy-paste grant scripts published for each supported source.

## 6. The Connections List

The list is a table, not a card grid: operators compare connections against each other (which agent version, which is stale, which has no streams) and comparison demands aligned columns.

### 6.1 Columns

Shown by default:

| Column | Content |
|---|---|
| Connection | Name in monospace, with a `source` / `target` role pill; the name links to the connection detail screen |
| Platform | Class and capture/apply mechanism, e.g. `Oracle 19c · direct redo`, `PostgreSQL 17 · logical` |
| Description | Operator-written purpose — what business system this is |
| Agent | Agent binary version and platform, or `agentless · hub-direct` |
| Heartbeat | Time since the last agent heartbeat (or hub reachability probe when agentless), relative |
| Status | `Healthy` / `Unreachable` pill derived from the heartbeat and last validation result |
| Test | Per-row button running the connectivity test (§10) |

Available through the column chooser, hidden by default:

| Column | Content |
|---|---|
| Host / endpoint | Resolved host and port, or the store URI |
| Created | Date the connection was defined |
| Created by | Full name of the user who defined it |
| Streams | Count of streams using this connection |
| Last test | Outcome and age of the most recent connectivity test |

The Test button is itself a hideable column — operators who never test from the list can reclaim the space. The Connection column is locked on; hiding the identifier is never useful.

### 6.2 Sorting and filtering

Every visible header is a sort control: click to sort, click again to reverse, with a `▲`/`▼` indicator on the active column. Numeric columns (Heartbeat, Streams) sort numerically, not lexically — a 14-minute-stale agent must not sort between 1s and 2s because "1" precedes "2". The default order is **Connection descending**, with the indicator visible on load so the sort state is never implicit.

Each visible column carries a filter box under its header. Filters are substring matches, combine across columns (AND), and are reflected immediately; when nothing matches, the table shows an explicit empty state rather than an ambiguous blank area. The Connection filter also matches the role, so `target` narrows to targets without a separate control.

### 6.3 Persistence and scoping

Column visibility and sort order are **per user**, stored with the operator's other workspace preferences and restored at sign-in; two operators sharing a fleet keep their own table setups. Filters are session-only — they are a transient act of looking, not a preference.

**Connections belong to the virtual fleet, not to a stream.** The Connections screen sits directly under its virtual fleet alongside Jobs and Events, while Tables, Monitoring, and Admin sit under each individual stream. Opened at the virtual-fleet level, the list shows every connection used by that virtual fleet's streams, plus connections created there that no stream uses yet; opened from a stream it narrows to that stream's source and target. One scope rule drives all three virtual-fleet screens, so a count shown in the Global fleet console always matches what the screen it opens contains.

## 7. Connection Detail

The detail screen is organized as three configuration cards plus a membership table, so an operator can read the whole connection without scrolling through a form.

**Header** — name, role pill, status pill, platform and description, and a **Test connection** action.

**Agent card** — for agent-based connections: mode, agent binary, enrollment method, agent host, agent port, and heartbeat age. For agentless connections: a plain statement that the hub connects directly, with the reachability probe age. Each card has an Edit action opening the corresponding dialog (§9).

**Database connection card** — host, port, database, and user; for Oracle also `ORACLE_HOME` and the connect path (`Local · SID x` or `TNS · x`). A standing note states that credentials are vaulted on the hub and never written to agent disk or logs — the credential-handling promise from §5 restated where the operator can act on it.

**Source and target properties card** — the resolved capture or integrate method plus the enabled options, so the effective configuration is visible without opening the editor.

**Stream membership** — one row per stream using this connection: stream name (linking to the stream), replication status, the role the connection plays *in that stream*, table count, and average daily volume. This is the blast-radius answer: an operator looking at an unreachable connection sees immediately which streams are affected. An **Add to an existing stream** action starts the membership change; a connection with no streams shows an explicit empty state rather than an empty table.

## 8. Creating a Connection

A connection is created through a five-step wizard, not a single dense form. Each step confirms before the next opens, completed steps collapse to a one-line summary with an Edit action, and a persistent rail carries the connection name, description, and step progress — so the operator always knows what they have committed to and what remains.

| Step | What it asks | Notes |
|---|---|---|
| 1 | **Select connection type** | Every supported platform, filterable by All / Sources / Targets, each stating the roles it can take. The choice seeds the platform's default port and constrains every later step |
| 2 | **Select agent connection** | Agent vs hub-direct with each mode's cost stated; agent host and port; regular vs RAC-cluster agents; test agent connection; configure agent service; certificate state; authentication method |
| 3 | **Configure database connection** | Platform-shaped: Oracle asks ORACLE_HOME and local-SID or TNS; others ask host, port, database. User and password with the vaulting statement |
| 4 | **Configure capture / integrate** | Role (only what the class supports) and method, with the class's options and the same configuration-time cross-validation as the edit dialog |
| 5 | **Stream membership** — optional | Save unattached (the default) or attach to streams in the current virtual fleet now |

Three rules govern the wizard:

**A connection exists on its own.** Membership in a stream is a separate act, deliberately optional and defaulted off: an operator defining a database before any stream needs it must not be forced to invent a stream. The confirmation states which happened, and an unattached connection says so plainly on its detail screen with an action to attach it later.

**A name is required and unique.** Nothing is saved without one — the name is how every stream, job, and event refers to the connection — and a duplicate is refused at creation rather than producing two rows an operator cannot tell apart. A missing method is refused the same way, and the wizard returns to the step that needs attention.

**What the operator entered is what the console shows.** Every value the wizard collects — agent host and port, RAC choice, connect path, SID or TNS, ORACLE_HOME, method, and each enabled option — is stored on the connection and rendered on its detail screen. No screen substitutes a derived default for a field the operator left blank; blank reads as blank, and editing a blank field starts empty rather than pre-filled with a display placeholder. A newly created connection enters as **Enrolling** with no heartbeat until its first one arrives.

## 9. Configuration Dialogs

All three dialogs share one contract: they state the trade-off of each choice inline, they validate against the class capability matrix rather than accepting anything and failing at runtime, and they carry a **Test connection before saving** checkbox that is checked by default and can be unchecked. Saving untested is legitimate — an operator configuring a database that is down for maintenance must be able to record the configuration — so the product allows it, says so in the confirmation, and defers validation to the next heartbeat or capability check. Every save is recorded in the event ledger.

### 9.1 Agent dialog

Two mutually exclusive modes, presented as cards with their trade-offs stated rather than as a bare toggle:

- **Connect via agent** — an enrolled binary on or near the database host, over mTLS. Reduces network cost, distributes CPU load, and enables capture directly from the database logging system.
- **Agentless** — the hub connects to the endpoint itself. Simpler and zero-footprint; all capture load and network cost land on the hub.

In agent mode the dialog exposes **agent host** and **agent port**, a **Test agent connection** action (reachability, latency, mTLS handshake, certificate verification, and a hub/agent version match check), and a **Configure agent service** action for service account, spool directory, log level, and upgrade ring.

A certificate panel states that the agent's public certificate is pinned, shows its fingerprint, and offers two actions: **rotate certificate** (the agent picks up the new pinned certificate on its next heartbeat; the old certificate is honored for a grace period) and **re-issue enrollment token** (single-use, short-lived, recorded in the ledger). Agent user and password complete the section.

Switching a connection to agentless is a visible change, not a silent one: the Agent column in the list and the detail card both re-render to `agentless · hub-direct`.

### 9.2 Database connection dialog

Platform-shaped rather than generic. For **Oracle**:

- `ORACLE_HOME`
- A connect-path choice: **Local connect to database** with a **SID** — which requires the agent to run on the Oracle host itself — or **Oracle TNS**, connecting over SQL*Net using either a name defined in `tnsnames.ora` or the `[//]HOST[:PORT]/SERVICE_NAME` form. Saving a TNS string re-derives host, port, and service for display everywhere else in the console.

For other platforms: host, port, and database. Both variants take the database **user** and **password**, with the vaulting statement repeated at the point of entry.

### 9.3 Source and target properties dialog

Method selection is the primary control and is filtered to what the class actually supports.

**Oracle sources** — capture method: **Direct redo** (reads online redo and archive logs directly, no LogMiner; lowest latency, requires log access on the Oracle host) or **Archived-log only** (reads archived logs as they close; no online redo access needed, latency bounded by the log switch interval).

The dialog cross-validates against the database connection: choosing Direct redo while the connection is TNS raises an inline warning that direct redo only works if the TNS connection is loopback — the agent running on Oracle's own machine — or if a local SID connection is used. This is the class of misconfiguration that otherwise surfaces as a runtime capture failure, caught at configuration time as §4 requires.

Oracle options: **Pluggable database** (capture from a PDB requires root-container access) and **SAP source** (reads SAP dictionary metadata during table selection; required to unpack cluster and pool tables). Under **Advanced capture properties**, collapsed by default: extra redo archive directory with path, show invisible columns, intermediate staging directory with path, and case-sensitive names.

**PostgreSQL sources** — logical replication slot, with slot and publication names.

**SQL Server and DB2 sources** — transaction log reader and `db2ReadLog` respectively.

**Targets** — default integrate method: **Continuous** (apply each change as it arrives; lowest latency), **Batched cycles** (accumulate and apply on a cycle; fewer target commits), or **Burst apply** (coalesce into set-based operations; best for warehouse targets). The value is a default that a stream may override. Options: create state tables automatically (exactly-once apply state) and case-sensitive names.

## 10. Connectivity Testing

One test action is reachable from three places — the list row, the detail header, and each dialog — and reports the same shape of result: on success, latency plus what was verified (mTLS handshake, certificate, version match, capability matrix); on failure, the specific cause and the remediation direction, e.g. an unreachable agent naming how long it has been unreachable and pointing at enrollment and network path. Consistent with §4, a failure never dead-ends in "contact support".

## 11. HVR Parity Matrix

**The model**

| HVR concept | This platform | Delta |
|---|---|---|
| Location = source/target storage place | Same | Kept |
| Location properties | Location properties, schema-validated | Machine-readable class capability matrix |
| Agent or agentless connection | Same | Same trade-offs, documented per class |
| Capability lists per DBMS (docs) | Generated capability matrix | Docs and enforcement from one source |
| Credential storage | Envelope encryption + external secret references | Rotation without restart |
| Runtime failures on bad config | Configuration-time validation suite | Errors link to public fix pages |

**The surface**

| HVR concept | This platform | Delta |
|---|---|---|
| Location list | Connections list | Sortable and filterable on every column; per-user column sets |
| Location properties dialog | Platform-shaped connection dialogs | Choices constrained by the capability matrix; trade-offs stated inline |
| Oracle ORACLE_HOME + local/TNS connect | Same | TNS string re-derives host/port/service for display |
| Capture method selection | Same | Cross-validated against the connect path at configuration time |
| Agent vs agentless | Same | Cost/benefit of each mode stated in the dialog; switching is visible in the list |
| Test connection | Same, from list, detail, and dialogs | Save-without-test explicitly supported and disclosed |
| — | Stream membership on the connection | Blast radius visible where the failure is diagnosed |

## 12. Test Plan

Phased; the standing rule applies (procedure executed, results observed, evidence archived — no procedure, no pass), and the full suite reruns as regression on every merge touching this area.

**Model phases**

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Validation and hygiene | LOC-01, LOC-02, LOC-03, LOC-04 | Misconfiguration fixtures + CI sweeps | Validator and secret handling implemented | All fixtures caught; canary sweeps green; matrix drift check green |
| B | Connectivity paths | LOC-05, LOC-06, LOC-07 | Integration lab incl. RDS-equivalent | Phase A exit; agentless paths implemented | BFILE, SELECT-only, and probe behaviors proven |

**Surface phases**

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Table behavior and scoping | CON-01, CON-02, CON-03, CON-14 | Playwright against seeded fleet fixtures | Connections list implemented | Sort, filter, and per-user column persistence proven across two accounts |
| B | Configuration dialogs and creation | CON-04, CON-05, CON-06, CON-07, CON-10, CON-11 | Misconfiguration fixture set from §12.1 | Phase A exit; dialogs implemented | Every fixture caught at configuration time with documented remediation |
| C | Testing and disclosure | CON-08, CON-09, CON-12, CON-13 | Integration lab incl. a deliberately unreachable agent | Phase B exit | Test results and save-without-test disclosure verified; ledger entries present |

### 12.1 Methods — the model

Connection testing centers on a **misconfiguration fixture set**: lab containers deliberately prepared with missing privileges (no supplemental logging grant, no replication role, unwritable stage), wrong versions, and dead listeners. The validation suite must catch every fixture at configuration time with the exact documented remediation (LOC-01) — a new connector is not done until its misconfiguration fixtures exist.

**Credential hygiene** is enforced by automated sweeps, not review: every test run greps all logs, API response captures, and configuration exports for planted canary credential strings; any hit fails the build (LOC-02, LOC-03). Rotation tests swap an external secret mid-stream and assert next-connection pickup with zero restarts against a live TPC-C load.

**Single-source-of-truth** for the capability matrix is verified structurally: a CI step regenerates the published matrix and the UI enforcement rules from the class declarations and diffs both against the shipped artifacts — any drift fails (LOC-04). **Probe behavior** (LOC-07) uses fault injection (listener kill, network partition) with assertions on detection latency and on probe query cost against the source (the probe's own load budget is a tested number, not a hope). Agentless paths (LOC-05, LOC-06) run in the integration tier against the RDS-equivalent lab container.

### 12.2 Methods — the surface

Table behavior is driven by Playwright against seeded fixtures, including a fixture whose heartbeat ages are chosen to fail a lexical sort (1s, 2s, 14m) — the numeric-sort criterion is unfalsifiable without it. Per-user persistence is proven by configuring distinct column sets on two accounts, reloading, and asserting neither leaked into the other.

Dialog validation reuses the misconfiguration fixture set: for connections, the decisive fixture is an Oracle connection reachable only over non-loopback TNS with Direct redo requested — the warning must appear at configuration time, before any job runs.

## 13. Test Procedures

### LOC-01 — Validation catches misconfiguration fixtures
**Preconditions:** The misconfiguration fixture set: lab containers each broken one way (no supplemental logging grant, no replication role, unwritable stage, unsupported version, dead listener).
**Steps:** (1) Attempt connection creation against each fixture. (2) Record the validation verdict and remediation text per fixture. (3) Confirm no job can be started referencing a failed connection. (4) Fix one fixture using exactly the remediation text; re-validate.
**Expected:** Every fixture fails validation naming the exact defect and remediation (including copy-paste grant statements); job start refused for invalid connections; the remediation text alone is sufficient to reach a passing validation.
**Evidence:** Per-fixture validation transcripts; remediation-followed re-validation record.

### LOC-02 — Credential rotation without restart
**Preconditions:** Connection using an external secret reference; live TPC-C stream through it; canary string embedded in the old password.
**Steps:** (1) Rotate the secret in the external store. (2) Force a reconnect (bounce the source listener briefly). (3) Verify the stream resumes using the new material with no stream or agent restart. (4) Sweep all logs for both old and new canary strings.
**Expected:** Reconnect succeeds on new credentials; zero stream restarts in the event log; zero canary hits in any log.
**Evidence:** Event timeline, log sweep output.

### LOC-03 — No credential material in API or exports
**Preconditions:** Connections configured with canary-marked stored credentials; full API response capture; GitOps export.
**Steps:** (1) Exercise every connection-related REST endpoint and capture responses. (2) Produce a configuration export via CLI. (3) Sweep captures and export for canaries.
**Expected:** Zero canary occurrences anywhere; export contains secret references or redaction markers only.
**Evidence:** Sweep output over the full capture set.

### LOC-04 — Capability matrix single source of truth
**Preconditions:** CI environment; a branch adding a fake capability to one class declaration.
**Steps:** (1) Run the doc/enforcement generation step on main; diff against shipped artifacts (expect clean). (2) On the branch, regenerate; verify the fake capability appears in both the generated matrix documentation and the UI enforcement rules. (3) Manually edit the shipped doc without changing the declaration; run CI.
**Expected:** Step 2 shows propagation to both artifacts from the single declaration; step 3 fails CI on drift.
**Evidence:** Diffs and CI results for all three runs.

### LOC-05 — Agentless Oracle via BFILE
**Preconditions:** Lab Oracle configured RDS-style (no host access, directory objects for redo/archive); no agent installed for it.
**Steps:** (1) Create the connection with agentless BFILE reachability; validate. (2) Activate a small stream; run a capture cycle against generated changes. (3) Compare.
**Expected:** Validation passes; capture completes over BFILE reads only (session audit shows no local file access); compare clean.
**Evidence:** Session audit, compare report.

### LOC-06 — SELECT-only connection boundaries
**Preconditions:** Lab source with a SELECT-only service account.
**Steps:** (1) Create the connection; validate for refresh mode. (2) Run a scheduled full refresh; compare. (3) Attempt to switch the stream to CDC mode.
**Expected:** Refresh path fully functional and verified; CDC switch refused at configuration time with the documented privilege list for that class.
**Evidence:** Compare report, refusal message capture.

### LOC-07 — Health probe detection latency and cost
**Preconditions:** Healthy connection under probe; probe interval configured; source session monitoring.
**Steps:** (1) Record probe query cost on the source over one hour (baseline load budget). (2) Kill the source listener. (3) Measure time to degraded state on the Connections screen and REST API. (4) Restore; measure time to healthy.
**Expected:** Degraded within one probe interval; recovery detected within one interval; probe cost within the documented budget.
**Evidence:** Timing measurements, source session cost report.

## 14. Acceptance Criteria (traceability matrix rows)

**The model** — LOC ids retained from `location.md` for traceability.

| ID | Criterion |
|---|---|
| LOC-01 | Connection creation with insufficient privileges reports the exact missing grants at validation time; no job ever starts against an invalid connection |
| LOC-02 | Credential rotation via external secret reference takes effect on next connection with zero stream restarts and zero plaintext appearing in any log (log audit) |
| LOC-03 | API responses and configuration exports containing a connection never include credential material (automated sweep) |
| LOC-04 | A class capability matrix change (e.g., new slicing type) propagates to both the generated documentation and UI enforcement from the single declaration |
| LOC-05 | Agentless Oracle connection via BFILE completes a capture cycle on a lab RDS-equivalent (no local agent) |
| LOC-06 | Scheduled-refresh-only connection with a SELECT-only account completes a full refresh; attempting to enable CDC on it is refused with the documented privilege list |
| LOC-07 | Connection health probes detect a dropped listener within one probe interval and surface degraded state on the Connections screen and REST API |

**The surface**

| ID | Criterion |
|---|---|
| CON-01 | The connections list shows Connection (with source/target role), Platform, Description, Agent, Heartbeat, and Status, plus a per-row test action that reports pass with latency or fail with cause |
| CON-02 | Every visible column is sortable, toggling ascending/descending with a visible indicator; the default order is Connection descending with the indicator shown on load; Heartbeat and Streams sort numerically |
| CON-03 | Per-column filter boxes combine across columns and show an explicit empty state; column visibility and sort order persist per user across sessions and never leak between users |
| CON-04 | The column chooser adds and removes columns including Host/endpoint, Created, Created by, Streams, and Last test; the Test action is hideable; the Connection column cannot be hidden |
| CON-05 | Connection detail shows agent mode (agent-based with host, port, binary, and heartbeat, or agentless), database connection, resolved source/target properties, and stream membership with the role played in each stream |
| CON-06 | The agent dialog switches between agent and agentless, exposes agent host and port, tests the agent (reachability, latency, mTLS, certificate, version match), and supports certificate rotation and single-use enrollment token re-issue |
| CON-07 | The Oracle database dialog exposes ORACLE_HOME and a local-SID or TNS connect path; a saved TNS string re-derives host, port, and service consistently across the console |
| CON-08 | Capture and integrate method choices are constrained to what the class supports, and Direct redo requested over a non-loopback TNS connection raises a configuration-time warning naming the loopback or local-SID requirement |
| CON-09 | Every configuration dialog defaults to testing before saving, allows saving untested, discloses in the confirmation which of the two occurred, and records the save in the event ledger |
| CON-10 | Connections are created through a five-step wizard (connection type, agent connection, database connection, capture/integrate, stream membership) whose completed steps collapse to editable summaries |
| CON-11 | A connection can be created and saved without attaching it to any stream; unattached is the default, the confirmation states which occurred, and the connection can be attached later from its detail screen |
| CON-12 | Creation refuses a missing or duplicate name and a missing capture/integrate method, naming the reason and returning to the step that needs attention |
| CON-13 | Every value entered during creation is stored on the connection and shown on its detail screen; no field displays a derived default in place of a value the operator left blank, and editing a blank field opens empty |
| CON-14 | Connections, Jobs, and Events are virtual-fleet screens and Tables, Monitoring, and Admin are stream screens; each list is scoped to the level it is opened from, and counts shown in the Global fleet console match the screens they open |

## 15. Open Questions

Whether connection definitions in GitOps exports should carry secret references only (recommended) or support sealed-secret material for fully offline bootstrap needs a decision with the CLI design. Probe intervals and their source-load budget need lab tuning. Per-class connection pooling policy (especially Oracle dictionary sessions) to be set during connector implementation.
