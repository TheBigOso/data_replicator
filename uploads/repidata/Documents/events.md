# Events — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design; the audit ledger
**Related:** `events-ui.md` (the console surface — filters, the expandable record, artifacts, planned retention/export/diff upgrades)

---

## 1. Purpose and Positioning

The event system is the platform's **ledger**: an append-only record of what happened, who did it, and what changed. HVR's event system serves two purposes and both are kept: it is the **audit trail** of user activity (this document's core), and it is the **state holder for long-running operations** (the event-driven task pattern, specified in the Jobs document, section 3 — referenced here, not restated). Every "versioned, attributed" promise made across this document set — stream definition changes, applied activation plans, job transitions, drift verdicts — resolves to a row in this ledger.

For the regulated enterprises this platform targets, the ledger is not plumbing; it is a requirement with a name. An ATO package, an ITAR audit, a SOX control test all ask the same question the ledger exists to answer instantly: *who changed what, when, and what exactly did it change?*

## 2. What Creates an Event — and What Doesn't

**Every state-changing operation creates exactly one audit event**, regardless of surface. Because the web UI, CLI, and GitOps apply all speak the one public REST API, there is a single enforcement point — the API layer — rather than HVR's enumerated list of commands that happen to write events. If it mutates the repository or commands the runtime (definition changes, activation plans, job start/suspend/disable, hub creation or freeze, location changes, alert configuration, imports), it is evented. Structurally, nothing state-changing can bypass the ledger, and EVT-01 sweeps the entire API surface to prove it.

**What doesn't create audit events**, kept from HVR because the reasoning is sound: read-only activity (views, exports, list calls — though data-preview reads *are* separately audited under the RBAC regime, SLC-13/compare report access, because reading row data is different in kind from reading configuration); and the routine activity of replication jobs themselves, which belongs in run logs (Jobs, section 5), not the ledger — a busy stream would otherwise drown the audit trail in heartbeats.

**Operational events** are the deliberate departure. Job state transitions, fired alerts, drift verdicts, agent enrollments and upgrades — HVR scatters these across log files; we record them as a second **event class** in the same ledger, because the 2 AM question is almost always a *joined* question: "the alert fired at 2:04 — what changed before that?" One timeline, filterable by class (`audit` / `operational`), answers it in one query instead of a log-correlation exercise.

## 3. The Event Record

Every event carries: a **unique monotonic event ID** plus timestamp (HVR identifies events by microsecond timestamp alone — an identifier that can collide and encodes nothing; ours is an ID that happens to have a timestamp); the **type** (from the published type catalog); the **actor** — a user identity, an API token identity, or a GitOps commit reference, so automation is attributed as precisely as humans; the **scope** — hub (or repository-wide for the few operations above hub level), stream, locations, and tables affected; and the **payload** — for definition changes, the field-level diff (the same diff the stream version history shows: one mechanism, surfaced twice); for plans, the applied plan; for task events, the linkage to job, run log, and artifacts.

### 3.1 Worked example — the auditor's question

*"Who changed the ORDERS stream in March, and what exactly changed?"* One filtered query: scope = stream ORDERS, class = audit, time = March. The answer is a short list of events, each with actor, timestamp, and field-level diff — including the one applied via GitOps, attributed to its commit. No log archaeology, no "we think it was the migration script." The same query is one screen in the UI's Events page and one CLI call, because they are the same API call.

## 4. Event States

Audit events are instantaneous: recorded complete, no lifecycle (HVR creates them in DONE state; same idea, stated plainly). Task events (Jobs, section 3) have the lifecycle: created **ACTIVE** (or **WAITING** when scheduled for a future time), terminating in **FINISHED** with a result of SUCCEEDED or FAILED — FAILED carrying its cause: `error`, `canceled` (operator), or **`superseded`**. Superseded is HVR's practical rule kept and named: creating a new compare or refresh event while a prior one for the same job is still pending cancels the prior one — the new intent wins — but where HVR silently marks it FAILED, ours says *superseded by event N*, so the trail explains itself. Interrupted task events **resume from checkpoint** rather than restarting (the slicing spec's checkpoint discipline is what makes this cheap), and the resume itself is visible in the event's history.

## 5. Immutability, Retention, Forwarding

The ledger is **append-only**: no API exists to modify or delete an event — the only mechanism that removes events is the retention policy, itself a configured, evented setting. Retention defaults are generous and the regulated-deployment guidance says "align with your audit cycle, or forward and keep forever."

**Forwarding** is where the defense story lives: events stream to **syslog** (the SIEM answer — Splunk, Sentinel, and kin ingest it natively), **webhook**, and **file drop** (the air-gap answer, same pattern as the sync report's delivery), each carrying the full structured record. Forwarding is at-least-once with event IDs enabling receiver-side dedup, and a gap detector (monotonic IDs make gaps provable) alerts if a forwarder falls behind. An enclave can therefore maintain its security-team-owned copy of the ledger outside the platform entirely — which is precisely what an accreditor wants to hear.

## 6. HVR Parity Matrix

| HVR events concept | This platform | Delta |
|---|---|---|
| Two purposes: audit trail + long-task state | Same two, task side owned by Jobs spec | Kept, cleanly split |
| Events from enumerated commands/UI operations | Every state-changing API call evented — single enforcement point | Structural, not a list |
| Read-only activity not evented | Same (data-preview reads separately audited) | Kept, with the RBAC carve-out |
| Job activity in logs, not events | Run logs kept; job transitions added as operational event class | One timeline for the joined question |
| Identified by microsecond timestamp | Monotonic event ID + timestamp | Collision-proof, gap-provable |
| Actor recorded | Actor: user, token, or GitOps commit ref | Automation attributed precisely |
| Scope: hub/repository, chn/loc columns | Same scope model, plus tables | Kept, extended |
| States: CURRENT/WAITING/DONE/CANCELED/FAILED | ACTIVE/WAITING → FINISHED(SUCCEEDED / FAILED: error, canceled, superseded) | Aligned with the Jobs rationalization |
| New event cancels same-job PENDING event | Same rule, cause named `superseded` with the successor's ID | Kept, self-explaining |
| Interrupted compare/refresh continues from checkpoint | Same, resume visible in event history | Kept |
| View via UI/CLI/API | Same three, one API | Parity rule |
| No built-in SIEM forwarding | Syslog + webhook + file-drop forwarders, gap-detected | New — the accreditor's copy |

## 7. Test Plan

Phased; standing rule applies (procedure executed, results observed, evidence archived — no procedure, no pass). Full EVT suite reruns on merges touching the API layer, event store, or forwarders — with EVT-01 in particular rerunning on *any* API change, since completeness is a property of the whole surface.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Ledger completeness and integrity | EVT-01, EVT-02, EVT-06 | API sweep harness + lab hub | Event store implemented | Whole-surface sweep green; immutability and attribution proven |
| B | Timeline and task lifecycle | EVT-03, EVT-04, EVT-07 | Integration lab, virtual clock | Phase A exit | Filtering, supersede, resume, and scope accuracy proven |
| C | Forwarding | EVT-05 | Lab SIEM sink + namespace egress control | Phase B exit | All three forwarders exactly-once-effective, air-gap proven |

### 7.1 Methods

Completeness is tested as a **surface sweep**: a harness enumerates every endpoint from the OpenAPI specification, classifies each as state-changing or read-only, invokes all of them, and asserts exactly-one-event for the former and zero for the latter — so a new endpoint added without event coverage fails CI by construction, which is the point of the single enforcement point. Integrity tests attack the ledger (mutation attempts, deletion attempts, out-of-order ID injection). Timeline tests run scripted multi-actor scenarios (UI user, API token, GitOps apply, concurrent task events) and diff query results against the script. Forwarding tests kill and resume forwarders mid-stream to prove at-least-once with provable gaps.

## 8. Test Procedures

### EVT-01 — Whole-surface completeness sweep
**Steps:** (1) Generate the endpoint inventory from the OpenAPI spec; classify state-changing vs read-only. (2) Invoke every endpoint against the lab hub (fixtures per endpoint). (3) Assert exactly one audit event per state-changing call with correct type and payload; zero events from read-only calls. (4) Add a mock state-changing endpoint without event coverage; verify CI fails.
**Expected:** Perfect one-to-one for state-changing; zero for read-only; the uncovered-endpoint canary fails CI.
**Evidence:** Sweep matrix (endpoint → events), CI canary result.

### EVT-02 — Immutability
**Steps:** (1) Attempt to modify and delete events via every conceivable path: API (no such endpoints — verify), direct repository access under the platform's own DB role (permissions audit). (2) Verify retention is the only removal mechanism and that changing retention settings is itself evented. (3) Verify ID monotonicity under concurrent event creation (load test).
**Expected:** No modification path exists; retention-only removal; retention changes evented; IDs strictly monotonic under concurrency.
**Evidence:** API surface audit, DB permission audit, concurrency ID sequence.

### EVT-03 — Unified timeline and filtering
**Steps:** (1) Run a scripted scenario: definition changes by two users, a GitOps apply, job transitions, a fired alert, a drift verdict — interleaved. (2) Query the timeline with each filter (class, actor, scope, time range) and combinations. (3) Diff every result set against the script's ground truth.
**Expected:** Every filter exact; the joined question ("what changed before the alert?") answerable in one scoped query whose result matches the script.
**Evidence:** Result-vs-script diffs (empty) per filter.

### EVT-04 — Task lifecycle: supersede and resume
**Steps:** (1) Create a compare event; while ACTIVE-pending, create a second for the same job; assert the first terminates FAILED(superseded) referencing the second's ID. (2) Start a large sliced compare event; kill the hub mid-run; restart; assert the event resumes from checkpoint (slices done stay done) and its history shows the interruption and resume. (3) Verify the resumed run's final report equals an uninterrupted run's (CMP-08 alignment).
**Expected:** Supersede exact and self-explaining; resume from checkpoint with visible history; identical final artifact.
**Evidence:** Event records with linkage, resume history, report diff (empty).

### EVT-05 — Forwarding: syslog, webhook, file drop
**Steps:** (1) Configure all three forwarders; run the EVT-03 scenario; verify every event arrives at each sink with full structured content, dedupable by ID. (2) Kill the syslog forwarder mid-stream; resume; verify at-least-once delivery and that the gap detector fired during the outage. (3) Run the file-drop forwarder with hub egress blocked (namespace); verify full function with zero external connection attempts.
**Expected:** Complete delivery on all sinks; provable gap + alert during outage, closed on resume; file drop fully air-gapped.
**Evidence:** Sink captures vs ledger, gap alert record, empty egress capture.

### EVT-06 — Attribution across actor types
**Steps:** (1) Make equivalent definition changes as: a UI user, an API token, and a GitOps apply (commit ref). (2) Inspect the three events' actor fields and payloads.
**Expected:** Each attributed to its precise identity (user / named token / commit ref); payload diffs identical for identical changes.
**Evidence:** Three event records.

### EVT-07 — Scope accuracy
**Steps:** (1) Perform operations at each scope: repository-level (hub creation), hub-level (calendar change), stream-level (definition change), location-pair-level (a refresh event naming source and target), table-level (per-table override). (2) Verify each event's scope fields; query by each scope dimension.
**Expected:** Scope fields exact per operation; scope queries return exactly the right events.
**Evidence:** Scope field audit, query results vs expectation.

## 9. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| EVT-01 | Every state-changing API call produces exactly one audit event and read-only calls produce none, proven by a whole-surface sweep that fails CI on uncovered endpoints |
| EVT-02 | The ledger is append-only with retention as the sole, itself-evented removal mechanism; event IDs are strictly monotonic under concurrency |
| EVT-03 | The unified timeline answers scripted multi-actor scenarios exactly under every filter combination (class, actor, scope, time) |
| EVT-04 | Same-job pending events are superseded with the successor named; interrupted task events resume from checkpoint with visible history and identical final artifacts |
| EVT-05 | Syslog, webhook, and file-drop forwarders deliver every event with dedupable IDs; gaps are detected and alerted; file drop works fully air-gapped |
| EVT-06 | Actors are attributed precisely across UI users, API tokens, and GitOps commit references |
| EVT-07 | Event scope (repository, hub, stream, locations, tables) is recorded and queryable exactly |

> **Update (2026-07):** `fleet-hierarchy.md` adds fleet-level scopes and evented operations: fleet creation/enrollment, grant/revoke at every admin level, user create/disable/delete, and credential resets are all ledger events; denied cross-scope admin attempts are evented too (FLT-06, FLT-08).

## 10. Open Questions

Operational-event granularity needs a volume budget: per-cycle job transitions on a busy hub could dwarf the audit class — likely a configurable operational-class verbosity with a sane default, decided with lab numbers. Retention defaults per deployment profile (commercial vs regulated) need field input. Whether the ledger should offer cryptographic chaining (each event hashing its predecessor — tamper-evidence beyond append-only) is a strong candidate for the defense tier; cost and key-management implications need the security-architecture design pass.
