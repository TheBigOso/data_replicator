# Location — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design; connector-specific requirements live with each connector

---

## 1. Purpose and Positioning

A **location** is a storage endpoint the platform captures changes from (source location) or integrates changes into (target location): a database, or a file store. Locations are defined once, centrally, in the repository, and referenced by any number of channels — connection details, credentials, and reachability are location concerns; what to replicate is a channel concern. This mirrors the HVR concept while tightening the parts HVR leaves loose: capability discovery, credential handling, and configuration-time validation.

## 2. Location Model

Every location carries: a unique name (fully qualified naming supported so `PROD.ERP01` and `TEST.ERP01` coexist unambiguously); a class (Oracle, PostgreSQL, SQL Server, DB2 LUW, Snowflake, Databricks, Kafka, S3/ADLS, ...); connection properties (host, port, service/database, cloud stage details); a reachability method (which agent serves it, or agentless); credentials (see section 5); and role eligibility (source, target, or both — derived from the class capability matrix, not asserted by the user).

### 2.1 Location classes and the capability matrix

Each class declares, in machine-readable form, exactly what it supports: capture methods available (log-based, scheduled-refresh-only), integrate methods (burst, continuous), refresh/compare support, slicing types available, data type mappings, and version ranges. The published capability matrix (transparency principle) is generated from these declarations, so documentation and enforcement share one source of truth. The UI constrains choices to what the class actually supports at configuration time rather than failing at job runtime.

Scheduled-refresh-only sources deserve emphasis: any database reachable by SELECT with a read-only account can be a source location in refresh mode (see Scheduler and Refresh Modes). This expands the source universe far beyond the log-based connector list and gives sales a soft landing — start with SELECT-only privileges, upgrade the location to CDC when access matures.

## 3. Reachability: Agent and Agentless

A location is reached either through a named agent (the normal case — the agent co-located with or near the data store performs the heavy work) or agentlessly, where the hub or a designated agent connects directly over the DBMS protocol: PostgreSQL wire protocol with logical replication, Oracle SQL*Net including BFILE access to redo/archive files (the path that covers Amazon RDS for Oracle and hosts where no agent may be installed). Agentless trades performance and offload for zero-footprint access; the choice is per location and the trade-off is documented per class.

## 4. Configuration-Time Validation

Creating or editing a location runs a validation suite immediately: connectivity, authentication, privilege sufficiency for the intended role (e.g., supplemental logging grantable, replication slot creatable, stage writable), and version support. Results are stored and displayed on the Locations screen with a health state (reachable, degraded, failing) refreshed by lightweight periodic probes. Every failure links to a public documentation page naming the missing privilege and the exact grant statement — no "contact support" dead ends.

## 5. Credential Handling

Credentials are stored in the repository under envelope encryption; plaintext never appears in logs, API responses, exports, or the UI after entry. Where the customer runs a secrets manager, a location may reference an external secret (vault path) instead of storing material at all — the serving agent resolves it at connect time. Rotation is supported without pipeline restart: the next connection attempt uses the new material. Service-account philosophy per class is documented (least privilege, read-only where the mode allows it), with copy-paste grant scripts published for each supported source.

## 6. HVR Parity Matrix

| HVR concept | This platform | Delta |
|---|---|---|
| Location = source/target storage place | Same | Kept |
| Location properties | Location properties, schema-validated | Machine-readable class capability matrix |
| Agent or agentless connection | Same | Same trade-offs, documented per class |
| Capability lists per DBMS (docs) | Generated capability matrix | Docs and enforcement from one source |
| Credential storage | Envelope encryption + external secret references | Rotation without restart |
| Runtime failures on bad config | Configuration-time validation suite | Errors link to public fix pages |

## 7. Test Plan

Phased plan; the standing rule applies (procedure executed, results observed, evidence archived — no procedure, no pass), and the full suite reruns as regression on every merge touching this area.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Validation and hygiene | LOC-01, LOC-02, LOC-03, LOC-04 | Misconfiguration fixtures + CI sweeps | Validator and secret handling implemented | All fixtures caught; canary sweeps green; matrix drift check green |
| B | Connectivity paths | LOC-05, LOC-06, LOC-07 | Integration lab incl. RDS-equivalent | Phase A exit; agentless paths implemented | BFILE, SELECT-only, and probe behaviors proven |

### 7.1 Methods

Location testing centers on a **misconfiguration fixture set**: lab containers deliberately prepared with missing privileges (no supplemental logging grant, no replication role, unwritable stage), wrong versions, and dead listeners. The validation suite must catch every fixture at configuration time with the exact documented remediation (LOC-01) — a new connector is not done until its misconfiguration fixtures exist.

**Credential hygiene** is enforced by automated sweeps, not review: every test run greps all logs, API response captures, and configuration exports for planted canary credential strings; any hit fails the build (LOC-02, LOC-03). Rotation tests swap an external secret mid-pipeline and assert next-connection pickup with zero restarts against a live TPC-C load.

**Single-source-of-truth** for the capability matrix is verified structurally: a CI step regenerates the published matrix and the UI enforcement rules from the class declarations and diffs both against the shipped artifacts — any drift fails (LOC-04). **Probe behavior** (LOC-07) uses fault injection (listener kill, network partition) with assertions on detection latency and on probe query cost against the source (the probe's own load budget is a tested number, not a hope). Agentless paths (LOC-05, LOC-06) run in the integration tier against the RDS-equivalent lab container.

## 8. Test Procedures

### LOC-01 — Validation catches misconfiguration fixtures
**Preconditions:** The misconfiguration fixture set: lab containers each broken one way (no supplemental logging grant, no replication role, unwritable stage, unsupported version, dead listener).
**Steps:** (1) Attempt location creation against each fixture. (2) Record the validation verdict and remediation text per fixture. (3) Confirm no job can be started referencing a failed location. (4) Fix one fixture using exactly the remediation text; re-validate.
**Expected:** Every fixture fails validation naming the exact defect and remediation (including copy-paste grant statements); job start refused for invalid locations; the remediation text alone is sufficient to reach a passing validation.
**Evidence:** Per-fixture validation transcripts; remediation-followed re-validation record.

### LOC-02 — Credential rotation without restart
**Preconditions:** Location using an external secret reference; live TPC-C pipeline through it; canary string embedded in the old password.
**Steps:** (1) Rotate the secret in the external store. (2) Force a reconnect (bounce the source listener briefly). (3) Verify the pipeline resumes using the new material with no pipeline or agent restart. (4) Sweep all logs for both old and new canary strings.
**Expected:** Reconnect succeeds on new credentials; zero pipeline restarts in the event log; zero canary hits in any log.
**Evidence:** Event timeline, log sweep output.

### LOC-03 — No credential material in API or exports
**Preconditions:** Locations configured with canary-marked stored credentials; full API response capture; GitOps export.
**Steps:** (1) Exercise every location-related REST endpoint and capture responses. (2) Produce a configuration export via CLI. (3) Sweep captures and export for canaries.
**Expected:** Zero canary occurrences anywhere; export contains secret references or redaction markers only.
**Evidence:** Sweep output over the full capture set.

### LOC-04 — Capability matrix single source of truth
**Preconditions:** CI environment; a branch adding a fake capability to one class declaration.
**Steps:** (1) Run the doc/enforcement generation step on main; diff against shipped artifacts (expect clean). (2) On the branch, regenerate; verify the fake capability appears in both the generated matrix documentation and the UI enforcement rules. (3) Manually edit the shipped doc without changing the declaration; run CI.
**Expected:** Step 2 shows propagation to both artifacts from the single declaration; step 3 fails CI on drift.
**Evidence:** Diffs and CI results for all three runs.

### LOC-05 — Agentless Oracle via BFILE
**Preconditions:** Lab Oracle configured RDS-style (no host access, directory objects for redo/archive); no agent installed for it.
**Steps:** (1) Create the location with agentless BFILE reachability; validate. (2) Activate a small channel; run a capture cycle against generated changes. (3) Compare.
**Expected:** Validation passes; capture completes over BFILE reads only (session audit shows no local file access); compare clean.
**Evidence:** Session audit, compare report.

### LOC-06 — SELECT-only location boundaries
**Preconditions:** Lab source with a SELECT-only service account.
**Steps:** (1) Create the location; validate for refresh mode. (2) Run a scheduled full refresh; compare. (3) Attempt to switch the pipeline to CDC mode.
**Expected:** Refresh path fully functional and verified; CDC switch refused at configuration time with the documented privilege list for that class.
**Evidence:** Compare report, refusal message capture.

### LOC-07 — Health probe detection latency and cost
**Preconditions:** Healthy location under probe; probe interval configured; source session monitoring.
**Steps:** (1) Record probe query cost on the source over one hour (baseline load budget). (2) Kill the source listener. (3) Measure time to degraded state on the Locations screen and REST API. (4) Restore; measure time to healthy.
**Expected:** Degraded within one probe interval; recovery detected within one interval; probe cost within the documented budget.
**Evidence:** Timing measurements, source session cost report.

## 9. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| LOC-01 | Location creation with insufficient privileges reports the exact missing grants at validation time; no job ever starts against an invalid location |
| LOC-02 | Credential rotation via external secret reference takes effect on next connection with zero pipeline restarts and zero plaintext appearing in any log (log audit) |
| LOC-03 | API responses and configuration exports containing a location never include credential material (automated sweep) |
| LOC-04 | A class capability matrix change (e.g., new slicing type) propagates to both the generated documentation and UI enforcement from the single declaration |
| LOC-05 | Agentless Oracle location via BFILE completes a capture cycle on a lab RDS-equivalent (no local agent) |
| LOC-06 | Scheduled-refresh-only location with a SELECT-only account completes a full refresh; attempting to enable CDC on it is refused with the documented privilege list |
| LOC-07 | Location health probes detect a dropped listener within one probe interval and surface degraded state on the Locations screen and REST API |

## 10. Open Questions

Whether location definitions in GitOps exports should carry secret references only (recommended) or support sealed-secret material for fully offline bootstrap needs a decision with the CLI design. Probe intervals and their source-load budget need lab tuning. Per-class connection pooling policy (especially Oracle dictionary sessions) to be set during connector implementation.
