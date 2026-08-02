# Stream — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design; replication styles locked, action model reworked from HVR

---

## 1. Purpose and Positioning

A **stream** is the logical unit of replication: it connects source and target location groups, names the tables that flow between them, and carries every setting that shapes that flow — replication style, mode, schedule, filters, mappings, and error handling. Everything operational (jobs, checkpoints, the file log's per-stream sequences, events, compare runs) hangs off a stream.

Terminology note: earlier specifications and the UI use **stream** for what the user sees on the fleet dashboard. Formally, a stream is a stream plus its running jobs — the stream is the definition, the stream is the definition in motion. The API and repository use `stream`; the UI may present "stream" where it reads more naturally. One+ concept, two registers.

The deliberate departure from HVR is the configuration model. HVR expresses stream behavior as a flat list of **actions** (Capture, Integrate, Restrict, ColumnProperties, TableProperties, ...) attached to location groups — powerful, composable, and famously hostile: behavior emerges from the interaction of scattered action rows, and diagnosing "why is this table doing that" means mentally executing the action list. Our stream is a **structured, schema-validated definition**: tables, styles, filters, and transforms live where they apply, the UI presents them contextually (the stream-detail page *is* the configuration surface), and the whole definition round-trips through the REST API and CLI as a single reviewable document — which is what makes the GitOps workflow real.

## 2. Stream Structure

**DDL-capture publication status.** The planned `ddl-capture.md` specification is not yet published in this repository. DDL policy is designed here, but the capture-side mechanism for detecting and decoding source DDL remains a gated dependency; its acceptance criterion stays open until that specification and implementation exist.

### 2.1 Location groups

A stream connects a **source location group** to a **target location group**. Every source group contains at least one source-capable location; every target group at least one target-capable location (capability derived from the location class matrix — see the Location specification). Most streams have exactly two groups. Groups exist so a stream can address "all the regional order databases" as one side of the flow: adding a location to a group extends the stream to it without re-declaring tables and settings.

The standard topologies map onto groups directly: one-to-one (one location per group), broadcast (multiple locations in the target group), consolidation (multiple locations in the source group), and combinations of both. Cascading is expressed as chained streams — the intermediate database is the target of stream A and the source of stream B — rather than multi-hop groups inside one stream; the topology view renders the chain as one flow (see Replication Topologies, TOP-03/TOP-07).

### 2.2 Table set

The stream names its tables explicitly or by pattern (schema and name globs, fully qualified), with per-table overrides for style, key handling, and mapping. The DDL policy — what happens when the source schema changes — is set per stream with per-table override: adapt automatically (add the column, propagate the change), adapt-and-notify, or hold-and-alert for change-controlled targets. The policy model here is independent of the capture-side mechanism that detects and decodes source DDL from the log — one of the genuinely hard problems in this product category (Oracle redo without LogMiner especially) — which gets its own design document, `ddl-capture.md` (planned; see README). STR-07 is gated on that design pass.

### 2.3 Settings, not scattered actions

What HVR expresses as action rows becomes structured settings at the level where they belong: stream-level (mode, schedule, style default, DDL policy, error handling), table-group-level (shared settings for a named set of tables — section 2.4), location-group-level (integrate method, parallel writers), and table-level (style override, filters, column mappings, soft-delete column naming). Every setting is a named field in the stream schema — validated at save time, documented in the generated reference, diffable in Git. Behavior never emerges from interaction at a distance.

Because settings now live at four levels, the **resolution order is explicit and published**: a table's effective setting is its own override if present, else its table group's, else the stream default (location-group settings apply to the location side of the flow and compose orthogonally). And it is **visible**: the UI's per-table effective-settings view shows every resolved value *with its provenance* — "schema mapping: `snowf_a`, from table group GROUP_A" — so nobody ever reverse-engineers where a behavior came from. That provenance display is the structured-settings answer to HVR's action archaeology.

### 2.4 Table groups

A **table group** is a named set of tables within a stream that share settings. Each table belongs to exactly one group; ungrouped tables land in the default group **GENERAL**. Group names are uppercase identifiers.

The motivating case is the heterogeneous many-schema stream. An Oracle → Snowflake stream with 1,000 tables — 800 in source schema `ora_a` bound for target schema `snowf_a`, 200 in `ora_b` bound for `snowf_b` — needs exactly two groups and four settings: GROUP_A carries source-schema `ora_a` and target-schema `snowf_a`; GROUP_B carries `ora_b`/`snowf_b`. Without groups, that stream needs the same schema mapping repeated hundreds of times (or, in HVR, four TableProperties action rows — groups are the one place HVR's action model was already economical, so we keep the economy and add the visibility).

Group assignment happens at table selection: manually (name a group in the selection dialog), by **auto-assign from schema** (each table's group derives from its source schema name — the right default for the many-schema case, and the assignment is then locked to the schema), or later by re-grouping in the definition editor (a versioned change like any other). Group membership can also be declared by pattern in GitOps definitions, with the same zero-match validation that table patterns get.

Anything table-level can be set at group level: schema and naming mappings, replication style, DDL policy, soft-delete column names, key overrides where a convention holds group-wide. The worked example above resolves per the ladder in 2.3 — and the effective-settings view shows it resolving, per table, with provenance.

### 2.5 Table identity and physical names

Every table in a stream has two kinds of name, and keeping them distinct is what makes renames, heterogeneous targets, and odd source names all tractable:

**The stream identity** (HVR's *Table Name*) is a stable lowercase ASCII identifier that the stream — and everything downstream of it — uses to refer to the table: settings attach to it, enrollment snapshots key on it, the file format's table IDs map to it, state and events reference it. It never changes when a physical table is renamed; it is the table's name *in the replication system*.

**The physical names** are what the table is actually called on each side: a per-side **base name** plus **schema**, composing to the *name in source* (`sales.customers`) and *name in target* (`product.customers`). Defaults are the obvious ones — base name defaults to the identity, schema defaults to the location's connect schema — and overrides are per-table structured settings resolved through the ladder of 2.3 (which is exactly how the table-group schema mapping of 2.4 works: GROUP_A's target schema is a group-level physical-name setting). The same identity-vs-physical split applies to **columns** (a column's stream identity vs its base name per side), to **file targets** (the identity names the table in file paths and record envelopes), and to **Kafka** (topic naming rules are a target-side physical-name constraint, validated from the capability matrix).

**Identity derivation is automatic and shown.** When a table is added, its identity derives from the source base name by published normalization rules: lowercased; truncated to the documented maximum length with a disambiguating suffix when needed; unsupported characters (spaces, symbols, non-ASCII scripts) transliterated or encoded per the published table; names colliding with the platform's reserved namespace prefixed (the reserved prefixes themselves are listed in the docs — HVR's `ii*` → `t_ii*` rule, generalized and documented rather than discovered). The transparency turn: any table whose identity differs from its source base name carries a **normalization badge** in the selection dialog and definition view stating exactly what was applied ("truncated from 34 chars", "transliterated: 顧客 → gu_ke") — and if two source tables normalize to the *same* identity, that is a **validation error at definition time** with both offenders named, never a silent overwrite or surprise suffix.

**The mapping cases, worked.** Rename across sides — source table `a` replicating to target table `b`: the identity stays `a` and the target-side base name is set to `b` (or, equivalently, identity `b` with a source-side base-name override — both directions supported; the effective-settings view shows whichever is in force). Same base name, different schemas: two stream tables, same base name, distinguished by identity and schema settings. One source table fanned into multiple target tables: multiple stream identities sharing one source physical mapping — supported explicitly, since each identity carries its own settings, style, and state.

## 3. Replication Styles

Styles dictate how source changes materialize on the target. Selectable per stream with per-table override; all three ship in v1 because target-side apply is where they live and the burst path must accommodate them from the start.

**Standard replica.** Inserts, updates, and deletes are mirrored; the target converges to a synchronized copy of the source. The default.

**Soft delete.** Source deletes become target updates: the row remains, marked deleted (configurable marker column, e.g. `_deleted` plus `_deleted_at`). For downstream consumers that need to know what vanished — warehouse dimensions, audit-adjacent reporting.

**TimeKey (append/audit).** Every change lands as a new row with change metadata: operation type, source commit position (SCN/LSN), commit timestamp, transaction sequence, and the change-origin lineage. Nothing is ever updated or deleted on the target — the table is an ordered audit trail of everything that happened. The natural style for data lakes, S3/ADLS file targets, and Kafka, and the reason the file format's metadata (origin, position, operation) is part of the published spec: TimeKey exposes it to customers directly.

Style interacts with keys: standard replica and soft delete require a key (or the no-PK handling from the capture layer); TimeKey requires none, which is also what makes it the escape hatch for keyless tables on append-friendly targets.

### 3.1 Worked example — one DML sequence, three materializations

Nothing makes the styles concrete like watching the same source activity land three different ways. Source table `CUSTOMERS(id PK, name, tier)`; the application performs three operations in order: insert row 1 as (Acme, gold); update its tier to platinum; delete row 1.

**Standard replica** mirrors each operation. After the insert the target has the row; after the update the row shows platinum; after the delete the row is physically gone. Final target state: zero rows — an exact mirror.

**Soft delete** mirrors the insert and update identically, but the delete becomes an update. Final target state: one row — `id=1, name=Acme, tier=platinum, _deleted=true, _deleted_at=<source commit time>`. Downstream consumers can see both current data and what vanished. If the application later re-inserts id 1, the configured re-insert rule applies (revive the marked row vs. version it — see Open Questions; the chosen rule is documented per target class).

**TimeKey** appends one row per change and never modifies anything. Final target state: three rows —

| _op | id | name | tier | _commit_pos | _commit_ts | _tx_seq | _origin |
|---|---|---|---|---|---|---|---|
| I | 1 | Acme | gold | 5482201 | 10:01:07 | 1 | PROD.ERP01/ch_orders |
| U | 1 | Acme | platinum | 5482310 | 10:03:22 | 1 | PROD.ERP01/ch_orders |
| D | 1 | Acme | platinum | 5482977 | 10:09:45 | 1 | PROD.ERP01/ch_orders |

The metadata columns are part of the published file-format specification, not an internal detail: `_op` (insert/update/delete, with key-updates represented as the documented delete+insert pair carrying a shared transaction identity), `_commit_pos` (source SCN/LSN — totally ordered per source), `_commit_ts` (source commit time), `_tx_seq` (ordering within a transaction), `_origin` (the change-origin lineage: the ordered chain of producing (location, stream) hops, hop-0 first — a single entry on a one-hop stream like this example, one entry appended per hop in a cascade; architecture spec 3.3). A customer can reconstruct exact source history, build slowly-changing dimensions, or feed an event stream from these columns — and because the spec is public, they can do it with their own tooling, not just ours.

**Key updates deserve a word**, because they are where replication products quietly differ: an update that changes the primary key is captured with both images and materialized per style — standard replica applies it as the documented delete-of-old-key plus insert-of-new-key inside one transaction; soft delete marks the old key and inserts the new; TimeKey records both events with shared transaction identity so the rekey is reconstructible. All three behaviors are in the public docs and covered by the STR-03/04/05 procedures.

## 4. Keys

Keys determine how the platform identifies rows — which makes them the quiet foundation under every update and delete a stream ever applies. HVR gets the model right and then hides it: the replication key is chosen automatically and silently, and the operator discovers the consequences (implicit keys, delete-and-reinsert updates) only when performance or behavior surprises them. We keep the model and surface every decision.

### 4.1 Primary keys vs replication keys

A **primary key** is the source database's own uniqueness declaration — enforced by transactional databases, often merely declarative on analytical ones. A **replication key** is what *this platform* uses to identify a row on the target. Every table in a stream replicating in standard-replica or soft-delete style has a replication key; TimeKey style needs none (nothing is ever updated or deleted on the target), which is precisely why TimeKey is the escape hatch for genuinely keyless tables.

### 4.2 Selection hierarchy — chosen automatically, shown always

At stream definition time the platform inspects each table and selects the replication key by the same hierarchy HVR uses, because it is the correct one:

1. The **primary key**, if one exists.
2. Otherwise, a **unique constraint or unique index whose columns are all mandatory** (an index on nullable columns cannot guarantee row identity — the Oracle single-nullable-column exclusion generalized: any unique index whose uniqueness can be defeated by NULLs is skipped). Non-unique indexes are never considered. Where multiple candidates qualify, the source dictionary's declared constraint outranks bare unique indexes.
3. Otherwise, the **implicit replication key**: all non-LOB columns of the table.

The departure from HVR is visibility: the chosen key, its **provenance** (primary / unique / implicit), and its columns are displayed per table in the stream definition UI and the API — and implicit-key tables carry a visible badge, because implicit keys change execution semantics (4.4) and the operator should learn that at design time, not from a slow integrate job. The creation wizard summarizes: "3 of 128 tables have no usable key — review before activation."

**Overrides** are per-table structured settings (not action archaeology): add columns to a key, replace the selection entirely, or designate columns for TimeKey ordering. Every override is versioned with the stream definition.

### 4.3 Implicit keys — exact semantics, no surprises

A table on the implicit key allows duplicate rows, and the platform must stay correct in their presence. The execution consequences, stated plainly in the docs and the UI badge's tooltip: every **update is treated as a key update** and replicated as a delete of the old image plus an insert of the new; every **delete is applied through a single-row-limited statement** so that deleting one of N identical rows removes exactly one, never all N. Correct, and slower — which is why the badge exists.

The **no-duplicate-rows** per-table flag (HVR's `NoDuplicateRows`) declares that a table without a unique constraint nonetheless contains no duplicate rows, unlocking the efficient direct-update path. HVR documents that incorrect use "can lead to errors" and leaves it there; we convert the hazard into a **guardrail**: setting the flag offers (and activation-time validation can enforce) a duplicate check — a grouped count over the implicit key columns — and refuses or warns per policy if duplicates actually exist. During refresh the check is nearly free (the data is already being read); the docs say exactly when it runs and what it costs.

### 4.4 Distribution keys — distributed targets

*Scope note: Redshift, Greenplum, and Teradata connectors are on the connector roadmap, not in the v1 target list (Snowflake, Databricks, PostgreSQL, file targets — see README). This section is deliberate forward design: the table-creation code carries the staging-alignment invariant from day one so it never needs retrofitting, and STR-22 enters the active traceability matrix when the first distributed-target connector lands.*

On distributed targets (Redshift, Greenplum, Teradata, and kin) every table the platform creates carries a **distribution key** controlling how rows spread across nodes. Two forms, HVR-parity: **explicit** (a per-table setting naming the column(s)) and **implicit** (derived from the first column of the replication key, tunable with an avoid-pattern for unsuitable columns and a column-count limit). Per-target constraints are enforced from the location capability matrix at definition time — Redshift's single-column limit is a validation message, not a runtime failure. Guidance is published with the concept: good distribution keys are unique or nearly so; skewed keys make skewed clusters.

One invariant is load-bearing enough to state and test independently: **burst staging tables always share the target table's distribution key.** Misaligned distribution between staging and target makes every burst merge shuffle across nodes — the integrate job gets slow or fails, and the cause is invisible unless you know to look. Our table-creation code enforces the invariant, the docs explain why it matters, and STR-22 proves it on every distributed target class. Target tables additionally receive an index on the replication key (unique when the table's key provenance or the no-duplicate-rows flag warrants it; non-unique otherwise); burst staging tables get none, deliberately — they are written once and merged away.

## 5. Stream Lifecycle

A stream is drafted (definition editable, validated continuously), activated (capture positions established — including the online-refresh-with-SCN coordination path for zero-downtime starts), running (jobs scheduled per mode), paused (checkpoints held, no data movement), and retired (jobs stopped; file-log residue GC'd; definition retained for audit). Definition changes to a running stream are versioned: every change records who, when, what diff — and the GitOps path applies the same versioned changes from a repository instead of the UI.

### 5.1 Creating a stream — the wizard

The creation wizard is HVR's five-step shape kept — operators know it — with each step's sharp edge filed. Structurally it is a **guided API composer**: every step issues the same documented calls the CLI would, the draft it builds is the ordinary versioned definition (save-and-exit at any step keeps a validated draft and creates zero runtime objects), and the finished product is exportable, so "what the wizard built" and "what GitOps would apply" are the same document.

**Step 1 — Name and type.** The stream name is validated against the published identity rules (2.5) as you type, not at save. The type selector offers the topology templates the platform actually ships: one-to-one, broadcast, consolidation — and *basic stream without locations* for skeleton-first workflows (kept from HVR; locations attach later). Bidirectional appears when v2 lands; multidirectional is stated as deliberately deferred with a link to the topologies spec — an honest absence, not a grayed-out mystery.

**Step 2 — Locations.** Create a new location inline (the full Location validation suite runs immediately — LOC-01's promise applies in the wizard too) or select existing ones, filtered by the capability matrix: a class that cannot capture never appears in the source picker, so the wrong choice is unmakeable rather than refused later. Confirming creates the **SOURCE and TARGET location groups automatically** (HVR parity), visible and renamable — the wizard's shortcut is the same structure section 2.1 specifies, not a parallel mechanism.

**Step 3 — Configure.** Replication style (standard replica, soft delete, TimeKey — stream default, per-table overrides later) **and the stream mode** — the selector HVR doesn't have: continuous CDC, scheduled refresh, or CDC plus scheduled compare. Mode belongs at creation because it changes what step 5 needs (a Mode 2 stream with a SELECT-only account skips capture setup entirely — the soft-landing path surfaces here, in the front door). File targets add their format/pattern settings in this step, per class.

**Step 4 — Tables.** Selection by list or pattern, with the design-time surfaces this document specifies appearing at the moment of choice: auto-assign table groups by schema (2.4), normalization badges on any identity that differs from its source name (2.5), the per-table key display with implicit-key badges and the summary line — "3 of 128 tables have no usable key — review before activation" (4.2) — and the DDL policy selector (adapt / adapt-and-notify / hold-and-alert), which is our answer to HVR's *Capture DDL Changes* checkbox: not whether to react to DDL, but how, per stream with per-table override.

**Step 5 — Complete.** HVR ends with three blind checkboxes — activate, initial refresh, start jobs. We end with the **computed activation plan** (6.1): the wizard requests the plan for exactly those choices, displays it step-by-step with the chained initial refresh included, shows the equivalent CLI/API invocation, and applies on approval — so the very first activation an operator ever performs already looks like every activation after it. Completion lands on the stream detail page (section 7), stream going green, with an *export what you built* action offering the definition for GitOps replay.


## 6. Activation and Deactivation

Activation is where a stream definition becomes running reality: jobs registered, capture positions established, supplemental logging enabled, state tables in place. HVR exposes this as a dialog of a dozen manually-checkable components — powerful, but the operator must know which components a given change requires, and several combinations are quietly destructive (recreating state tables discards recovery position; dropping burst tables mid-cycle breaks recoverability — hazards HVR documents rather than prevents). Our model keeps every capability and replaces the checklist with a **plan**.

### 6.1 Plan-based activation

Activation follows the plan/apply pattern operators know from Terraform. The hub diffs the stream definition against the actual state of every location — enrollment currency, supplemental logging present per table, state tables existing, jobs registered, capture positions — and computes the **minimal set of activation steps**, scoped automatically to only the affected locations and tables (a new table added to the stream yields a plan touching enrollment and supplemental logging for that table on the source, and nothing else). The plan is displayed step-by-step with impact notes; destructive steps are flagged and require explicit confirmation; the operator can widen or narrow scope before applying. HVR's "select only affected locations/tables" advice becomes computed behavior instead of tribal knowledge. Location-level steps execute in parallel by default (HVR's Location Parallelism, on by default), which matters most for supplemental logging across many tables.

Every plan displays its equivalent CLI/API invocation (parity with HVR's "show equivalent command line," guaranteed by the UI-as-pure-REST-client rule), can be exported for review or GitOps application, and every applied plan is recorded as a versioned, attributed event.

### 6.2 What the plan manages

**Jobs** — registered/recreated under the scheduler whenever the definition changed; always included in a post-change plan.

**Table enrollment** — the dictionary snapshot (object identifiers, column info) that log-based capture parses against. Improvement over HVR: enrollment is **per-table incremental** — only tables whose definitions or log-relevant settings changed are re-enrolled, instead of HVR's whole-stream regeneration whose cost grows with stream size.

**Supplemental logging** — enabled per table on log-based sources, as granular as the stream definition permits (key-only where sufficient, full where required), idempotent (validating existing logging is skipped for unchanged tables — the plan knows), parallelized across locations, and **never dropped on deactivation** (HVR's Oracle behavior, kept: the platform cannot know what else depends on it — the plan says so explicitly).

**PostgreSQL logical-replication objects** — on PostgreSQL sources, the plan creates the stream's **publication** (CREATE PUBLICATION scoped to the stream's tables, updated when the table set changes) and its named **replication slot**. HVR added the publication component only in 6.2.5; here both are first-class plan steps with a stated lifecycle. The slot is the sharpest object in the whole inventory: an orphaned slot pins WAL retention until the source's disk fills, while dropping it discards the capture position. The deactivation plan therefore always shows slot handling explicitly — retain (with the WAL-retention warning and a standing alert while a retained slot ages) or drop (with the position-loss warning) — never a silent default in either direction.

**State tables** — created on targets as part of first activation; they carry commit/transaction positions and are the loss-less recovery mechanism (including hub-loss recovery). **Recreation is a guarded destructive step**: it appears in a plan only when explicitly requested, is labeled with exactly what is lost ("recovery position for this target will be destroyed; do not do this after a network outage or a capture rewind unless you intend transactions to be re-evaluated"), and requires typed confirmation. The recovery-rewind ordering hazard (below) is enforced by the planner, not left to documentation.

**Change/auxiliary tables** — error tables (from on-error-save-failed), collision history tables (bidirectional), and burst staging tables. The plan protects data by default: error and history tables containing rows are excluded from cleanup unless explicitly selected; and **the plan refuses to drop burst tables while an integrate cycle is in flight** — it waits for cycle drain or requires a force flag whose consequence (loss of in-flight recoverability) is stated. Trigger-capture components (database triggers, generated procedures, source toggle/sequence tables) have no equivalent here — trigger capture is out of scope by design.

**File location state** — reset of the state directory on file locations, shown only when file locations are in the stream (the plan surfaces only relevant components, as HVR's dialog does).

### 6.3 Capture start and emit time

Two independent dials, kept from HVR because they solve a real problem — long-running transactions, endemic to ERP systems on Oracle:

**Capture start moment** — where log reading begins: now (default); **rewind to the start of the oldest currently-open transaction** (so nothing in-flight is missed); rewind by a fixed interval; or a custom point given as local/UTC time, transaction sequence, or Oracle SCN. Rewind is available as long as the transaction logs still exist; the plan checks availability before promising.

**Emit time** — where sending to targets begins, independently: emit everything from the capture point; emit only transactions **committed from now** (capture early to catch open transactions, but don't resend history); or delay emission until a specified time, sequence, or SCN. The interval-rewind-but-emit-from-now combination — capture from one minute ago, emit only commits after now — behaves exactly as HVR defines it: a change made 55 seconds ago and committed 50 seconds ago is not emitted.

**Recovery rewind to the target's integrate sequence** — the hub-failover path: a rebuilt hub reads the position from the target's state tables and resumes capture from there, losing nothing. Supports renamed streams/locations and multiple targets (rewinding to the oldest sequence among them). The planner enforces the ordering HVR only warns about: a plan containing both state-table recreation and recovery rewind is invalid, because recreation would destroy the very position the rewind needs.

The activation UI also surfaces the operational patterns these dials exist for — database upgrade windows (suspend capture, rewind past the upgrade noise afterward, no refresh needed if logs survive) — as documented recipes with their preconditions, per the transparency principle.

### 6.4 Post-activation refresh

A plan can chain an initial refresh (load source data to targets) with an explicit **table-creation policy**: leave target tables untouched; create only missing tables; create missing and alter/recreate mismatched layouts; or recreate all — with modifiers for keep-existing-structure (never remove extra target columns/indexes, never shrink), keep old rows on recreate, and no-index creation. Bulk refresh (truncate + bulk load path, with temporary index/constraint handling per target class) reuses the scheduler and slicing mechanics wholesale — one refresh engine, invoked from activation or from a schedule.

### 6.5 Worked example — what first activation actually does

The transparency principle applied to the product's most opaque moment. When an operator applies a first-activation plan for a CDC stream (Oracle source, Snowflake target, chained initial refresh), this is the actual sequence — every step visible in the plan beforehand and in the event log afterward:

1. **Validate** the stream definition against the location capability matrix and the live locations (privileges, versions, reachability) — anything wrong stops here, before any object is touched.
2. **Compute the plan** by diffing the definition against actual state on every location; display it with per-step impact notes and the equivalent CLI/API call.
3. On apply, per source location (in parallel across locations): **enroll tables** — query the database dictionary for each stream table's object identifiers and column layout, writing the per-table enrollment snapshot the redo parser will match log records against.
4. **Enable supplemental logging** per table at the granularity the stream requires (key-only where sufficient), skipping tables where correct logging already exists — the plan showed exactly which tables would be touched.
5. Per target location: **create the state tables** (schemas below) that will carry this stream's applied position and make recovery loss-less.
6. **Register the jobs** (capture, integrate, and the chained refresh) under the scheduler in PENDING state.
7. **Establish the capture position**: record the source's current position S (SCN here) — or the position the capture-start/emit-time dials specified — into the capture state. From this instant, the capture job will own every change from S forward.
8. **Run the chained refresh as-of S**: the refresh reads all stream tables at exactly position S (snapshot-consistent, sliced if configured), bulk-loading targets through the staging path. This is the zero-downtime handshake: refresh covers everything up to S, capture covers everything after S, and the integrate job knows to apply captured changes only past each table's refresh boundary — no quiesce, no gap, no overlap.
9. **Start capture and integrate**; the first change files flow through the hub file log; the stream goes green on the fleet dashboard.
10. **Record everything**: each step's outcome, timing, and any warnings land in the event log; the applied plan is archived as a versioned, attributed record.

HVR performs an equivalent dance, but the user sees a dialog and a result; here the choreography itself is documented, displayed, and logged — because an operator who understands step 8 can reason about every activation question that will ever come up at 2 AM.

### 6.6 What the platform stores — no hidden objects

Every object the platform creates in customer systems is enumerated in the public documentation with its purpose and schema. For a stream, the complete inventory is:

**In the repository (hub side):** the versioned stream definition document; per-table enrollment snapshots (object IDs, column layouts, the position they were taken at); job records and schedules; the applied-plan history; events. Never any row data.

**On the hub file store:** this stream's change files, named `<stream>/<sequence>` per the published format — headers (position range, schema epoch, checksum) inspectable with the shipped file-inspection tool, payloads encrypted.

**In each target database:** (non-database targets carry the documented position equivalent instead — the atomic manifest object on file targets, the compacted state topic on Kafka; see the architecture spec's delivery-semantics section, ARC-11/ARC-12) the state tables, with published schemas — per integrate location: applied transaction position (commit position, transaction id, integrate sequence), commit timestamp, and the recovery metadata that makes hub-loss failover possible (see STR-17). Updated in the same transaction as every apply — that co-transactionality is the exactly-once mechanism, stated plainly. Plus, where the stream configuration calls for them: burst staging tables (transient, per cycle), error tables (created on first error only), collision history tables (bidirectional streams), and soft-delete marker columns on replicated tables.

**In each source database:** nothing persistent beyond supplemental logging settings — with one honest exception: on **PostgreSQL sources**, log-based capture requires two documented objects, the stream's publication and its named replication slot (6.2), both plan-created, both inventoried, the slot carrying the WAL-retention warning stated there. Log-based capture creates no tables, no triggers, no procedures on sources — a sentence your DBA will ask for in writing, so it is in writing.

**Nowhere: generated scripts.** HVR's activation emits scripts among its runtime objects; this platform never generates executable scripts on any host — hub or agent — as part of activation or any other operation. Behavior lives in the signed binaries; the object-inventory sweep (9.1 Methods) would flag a stray script as an undocumented object and fail the run.

### 6.7 Entry points and the start policy

Activation is requestable from every surface that carries scope — the stream page, a location's page, the tables list, a single table's page, and the wizard's final step — and **the launch point pre-fills the plan's scope**: activating from a table's page requests a plan for that table; from a location's page, that location. HVR documents "select only affected locations/tables" as advice repeated on every page; here the surface you launched from has already done the selecting, and widening is one click. Where activation would be unavailable (no locations attached, nothing selected), the option is disabled with the reason in its tooltip — HVR's dialog behavior, kept, powered by the same validation that gates saves. And from a past activation's event page, **repeat** re-requests the plan with the recorded scope: because plans are computed against current state, repeating a fully-applied activation yields an *empty plan* — which is the correct answer, not an error.

Every plan ends with a **start policy**. *Start jobs* (the default) runs the orchestrated sequence of 6.5 — capture first, then the chained refresh once the first capture cycle has established the boundary, then integrate. *Leave suspended* applies every object change but parks capture and integrate in SUSPENDED — HVR's unchecked Force Start option, kept deliberately and named plainly, because staging an activation inside a change window and starting the jobs at the approved minute is how regulated shops actually operate. STR-27 exercises both policies.

### 6.8 Deactivation — the guarded teardown

Deactivation is the same plan machinery pointed in reverse: requestable from the same scoped surfaces as activation (stream, location, tables, single table — the launch point pre-fills scope, unavailable options disabled with the reason), computing the minimal step set, displaying it with impact notes, equivalent CLI shown, applied on approval, recorded as an event. Location-level steps parallelize as in activation. But teardown earns two rules activation doesn't need:

**The defaults are inverted from HVR's.** HVR's deactivation dialog defaults to *all components selected* — the default click drops state tables, capture position, queued transaction files, and (if collision detection is on) the active/active history, with the documentation reduced to pleading "ensure to unselect" the dangerous ones. Our default plan is **retention-first**: jobs stopped and removed, but state tables retained (re-activation resumes, STR-26), supplemental logging retained (6.2's never-drop rule), error and history tables with rows retained, and the PostgreSQL slot presented as the explicit retain-or-drop choice of 6.2. Every destructive component is *opt-in*, flagged with exactly what is lost, and the truly irreversible ones (state tables, capture position — "any open transactions being tracked will be lost") take the typed confirmation. Dropping everything is one deliberate act away, never the default click.

**Scope means scope.** HVR's dialog has two documented silent-widening surprises: table enrollment deletion "is always done for the entire stream" regardless of which tables you selected, and the supplemental-logging component "will be disabled for all tables in the stream, ignoring the table selection." Both are designed out: enrollment removal is per-table (the same incremental machinery as STR-14's enrollment), and any explicit logging-removal step — offered only where the DBMS and the capability matrix permit it at all — is scoped to exactly the selected tables. A plan never touches anything outside the scope it displays; the object-inventory sweep would catch it if it did.

## 7. Operating a Stream — the Detail Page

The stream (stream) detail page is the operating surface, and per the parity rule it is nothing but documented REST calls rendered — every pane and menu item below is reproducible with curl, and the ARC-07 sweep covers this page like any other. Three panes and a management menu, HVR's shape kept because operators know it, with the sharp edges filed.

### 7.1 Summary — the flow at a glance

A visual of the stream's data flow: source and target locations (click one → its Location Details page; multiple locations in a group → the filtered Locations list), the direction arrow reflecting the stream's topology, and the replicated-table count (click → the Tables view). Where HVR offers "View all actions," we offer **View effective settings** — the per-table provenance ladder of section 2.3 — because the question behind that click is always "why is this stream behaving this way," and a flat action list answers it worse than resolved values with their origins.

### 7.2 The graphs

**Integrated changes** — change volume over a selectable range (default 7 days; axis granularity follows the range, minute to day). **Latency** — the measured commit-to-apply delta (architecture walkthrough, step 12), shown as a min/max band per interval. Both draw from the metrics store, both are API-queryable series, and both link through to the stream's full Statistics page. Measured, not estimated — the latency band is the number the SLA conversation uses.

### 7.3 The jobs pane

Every job in the stream: type (activate, capture, refresh, integrate, compare, report), locations, live state (the Jobs spec's machine), recent errors, and a latency sparkline linking to statistics. A hide/show-inactive toggle keeps long-retired acyclic jobs out of the way. Bulk operations work the way lists should: click, shift-click a range, then suspend, start, or delete the selection. Per job: view run log (Jobs §5), start, suspend/unsuspend, delete, go-to-event, and cancel event (Jobs §3) — the event options appearing for the event-driven job types.

**Dismissible errors, with a trace.** HVR lets you hide an error with a click and it's simply gone. Here, dismissing an error is an **acknowledgment**: the error leaves the pane, and an audit event records who acknowledged what, when. Hidden problems leave a trail — the difference between tidying the dashboard and rewriting history.

**Graceful and force suspension.** Suspending a running capture or integrate job is graceful by default: the platform waits for the current replication cycle to complete before pausing, a drain dialog shows progress, and no in-flight transactions are stranded — HVR 6.1's graceful suspension, kept. **Force** suspension stops immediately — and here we improve on HVR, whose force kill is documented to possibly leave the job in an ambiguous PENDING state: because capture and integrate advance their checkpoints only on durable completion (architecture, life-of-a-change step 6 and step 9), a force stop is **checkpoint-safe by construction** — it costs at most redone work on resume, never correctness. The dialog says exactly that, so the operator choosing force knows the price is time, not data.

### 7.4 Managing the stream

The management menu, item by item: **Activate replication** (the plan-based flow of section 6) · **Compare data** and **Refresh data** (their specs) · **Create/alter target tables** (the creation-policy engine, 6.4) · **View stream log** · **Duplicate stream** — copies the definition into a new draft stream (identities, groups, settings preserved; no jobs, no state, no history — a clean template, and the duplicate event records its source) · **Rename stream** — versioned like any definition change; running replication is unaffected because everything internal keys on stream identity, and the recovery-rewind machinery already supports renamed streams (6.3) · **Export definition** (the GitOps round-trip, STR-02) · **Add existing locations** — into a location group, extending the stream without re-declaring tables or settings (2.1), via a computed minimal plan · **Deactivate replication** — a plan-based teardown with the same guardrails as activation: jobs stopped, supplemental logging **never** dropped (6.2), state tables retained by default so re-activation resumes rather than rebuilds.

### 7.5 Import, export, and classified data

Export and import move stream definitions between hubs — and the definition format is *the* definition format: the same document the CLI exports, GitOps applies, and STR-02 proves round-trips. Export works from a single stream's page or in bulk from the Streams list, with scope choices for including the referenced locations.

**Classified data — the honest options.** Definitions never contain plaintext secrets anywhere in this platform (location spec §5), so the export question is what to do about the secret-bearing location properties when locations are included. Three options, each stating its consequence:

- **Secret references only** (default): the export carries vault paths and named-secret references, no material at all — fully portable, nothing sensitive in the file, and the receiving hub resolves the same references. The GitOps-recommended mode.
- **Redacted**: placeholders in the file; the import summary lists exactly which objects need credentials re-entered, and activation validation (LOC-01) blocks until they are.
- **Transport-key encrypted**: secret values encrypted under a single-use key generated at export, for deliberate hub-to-hub moves; the key travels out of band, and importing without it degrades to redacted with the same explicit checklist. Requires the elevated export permission, and the export itself is an audit event naming scope and mode.

Two HVR options are deliberately absent: **"export stored (obfuscated) values" does not exist here** — obfuscation is not encryption, and a file of reversible secrets is a foot-gun we decline to ship; and HVR's wallet-encrypted mode (importable only to the same hub) is subsumed by secret references, which achieve same-hub portability without ever writing material to the file.

**Import is a plan.** Consistent with everything else: the import summary is a computed preview — streams, locations, groups, and tables to be created or changed — applied on approval and recorded as an attributed event (GitOps applies carry their commit reference). Name collisions offer **import under a new name** or **replace**: replace is a versioned definition change (the prior definition remains in history, like any edit), and the rename path fixes HVR's documented oddity — HVR appends a suffix to the stream *and imports suffixed copies of its locations that the renamed stream doesn't even use*. Here, collision handling is per object with an explicit mapping shown in the preview: existing locations are referenced, never cloned into orphans.

## 8. HVR Parity Matrix

| HVR stream concept | This platform | Delta |
|---|---|---|
| Channel connects source/target location groups | Same | Kept |
| ≥1 location per group; multi-location groups | Same | Kept |
| Cascading via multi-group channels | Chained streams, rendered as one flow | Simpler unit, same capability |
| Behavior via flat action list | Structured schema-validated settings | Contextual, diffable, no action archaeology |
| Standard replica | Standard replica | Kept, default |
| Soft delete (SoftDelete) | Soft delete with configurable marker columns | Kept |
| TimeKey | TimeKey with published change metadata | Kept; metadata spec is public |
| Per-table properties via actions | Per-table structured overrides | Same power, findable |
| AdaptDDL action | Stream/table DDL policy (adapt / notify / hold) | First-class, per-table |
| Channel definition scattered in repo tables | Single definition document, API/CLI round-trip | GitOps-ready |
| Activation: manual component checklist | Plan-based activation (computed diff, minimal scope) | Foot-guns become guardrails |
| Select affected locations/tables by operator judgment | Auto-scoped plan with operator override | Computed, not guessed |
| Whole-channel table enrollment regeneration | Per-table incremental enrollment | Cost scales with the change, not the stream |
| Supplemental logging validated per activation | Idempotent, per-table, parallel; never dropped on deactivate | Kept and accelerated |
| State-table recreation possible anytime (doc warning) | Guarded destructive step, typed confirmation, planner-enforced ordering vs recovery rewind | Prevented, not warned |
| Burst tables droppable mid-cycle (doc warning) | Plan refuses mid-cycle drop; waits for drain or explicit force | Prevented, not warned |
| Capture start moment: now / oldest open txn / interval / custom time-seq-SCN | Same four, with log-availability precheck | Kept, validated up front |
| Emit time independent of capture start | Same model, all delay variants | Kept |
| Recovery rewind to integrate sequence (hub failover) | Same, with renamed-stream and multi-target support | Kept, ordering enforced |
| Location parallelism option | Parallel by default | Default flipped to the sane choice |
| Show equivalent command line | Equivalent CLI/API shown on every plan; plan exportable | Structural, not a feature |
| Refresh after activation with creation options | Chained refresh with full creation-policy set, bulk load via the shared refresh engine | Kept, one engine |
| Replication key hierarchy (PK → mandatory unique → implicit all non-LOB) | Same hierarchy | Kept — it is correct |
| Key chosen silently | Key, provenance, and columns displayed per table; implicit-key badge; wizard summary | Surfaced at design time |
| Key overrides via ColumnProperties action | Per-table structured key settings, versioned | Findable, diffable |
| NoDuplicateRows: doc warning on misuse | No-duplicate-rows flag with duplicate-check guardrail (validate/refuse per policy) | Hazard becomes a check |
| Implicit-key semantics (update = delete+insert; single-row deletes) | Same semantics, documented in the UI badge itself | Kept, explained where it bites |
| Distribution keys: explicit / implicit from first key column, avoid-pattern, column limit | Same model; per-target limits validated at definition time | Kept; Redshift limit is a message, not a failure |
| Burst table distribution must match target (doc note) | Invariant enforced by table creation and tested (STR-22) | Prevented, not warned |
| Table groups (one group per table, GENERAL default, auto-assign by schema, uppercase names) | Same model | Kept — the economical part of the action system |
| Group-scoped actions (TableProperties on a group) | Group-scoped structured settings, anything table-level | Kept, broadened |
| Effective behavior inferred by reading action rows | Per-table effective-settings view with provenance | Resolution shown, never reverse-engineered |
| Table Name vs Base Name (identity vs physical, per side) | Stream identity vs physical names (base + schema per side) | Same model, kept |
| BaseName/Schema via TableProperties actions | Per-table (and group-level) structured physical-name settings, either side | Findable; both rename directions |
| Silent truncation, prefixing, character handling | Published normalization rules + per-table badge stating what was applied | Shown, not discovered |
| Normalization collisions possible | Identity collisions are definition-time validation errors naming both tables | Prevented, not warned |
| BaseName applies to columns, files, Salesforce API names | Identity/physical split for columns, file targets, Kafka topics (capability-matrix validated) | Kept, generalized |
| Channel Details page: summary, change graph, jobs pane | Same three panes, API-queryable series | Kept — operators know the shape |
| View all actions | View effective settings with provenance | Action archaeology retired at the UI too |
| Dismissible recent errors (gone on click) | Dismiss = acknowledgment, audited as an event | Tidying, not rewriting history |
| Graceful suspension (waits for cycle end) | Same, with drain progress | Kept |
| Force suspend may leave job in ambiguous PENDING | Force stop checkpoint-safe by construction — costs redone work, never correctness | Ambiguity designed out |
| Duplicate / Rename / Export / Add locations / Deactivate | Same menu; deactivate is a guarded plan (logging retained, state kept by default) | Kept; teardown gets the activation guardrails |
| Five-step creation wizard | Same five steps, each an API call; draft = ordinary versioned definition | Guided API composer, GitOps-exportable |
| Basic channel without locations | Kept | Skeleton-first workflows |
| Auto-created SOURCE/TARGET location groups with Capture/Integrate actions | Auto-created groups, visible and renamable; behavior via structured settings | Same shortcut, no hidden action rows |
| Configure step: replication style only | Style AND stream mode (CDC / scheduled refresh / CDC+compare) | The soft-landing path is in the front door |
| Capture DDL Changes checkbox | DDL policy selector (adapt / notify / hold), per-stream with table override | Not whether, but how |
| Completion: three blind checkboxes (activate, refresh, start) | Computed activation plan preview with equivalent CLI, applied on approval | First activation looks like every activation |
| Duplicate copies locations too | Duplicate references existing locations, never clones them | No orphan location copies |
| Rename of an activated channel requires deactivation (names embedded in jobs, config paths) | Rename is a metadata change; replication runs through it (identity-keyed internals) | No teardown to rename |
| Export secret handling: redact / transport-key / stored-obfuscated / wallet | Secret references (default) / redacted / transport-key; obfuscated export refused to exist | Reversible secrets never written to a file |
| Import: summary, rename-with-suffix or replace | Import is a computed plan; per-object collision mapping; replace is a versioned change | Suffixed orphan locations designed out |
| Redacted import: broken-connection warnings | Explicit post-import checklist; activation blocked by LOC-01 until credentials set | The gap is a checklist, not a surprise |
| Activation entry points across seven pages | Same reach; the launch surface pre-fills the plan's scope | Scoping advice becomes computed default |
| Disabled options with explanatory tooltips | Same, driven by the validation engine | Kept |
| Repeat Activate from Event Details | Repeat re-requests the plan against current state; fully-applied repeats compute empty | Idempotent by construction |
| Publication component (-ou, PostgreSQL, since 6.2.5) | Publication and replication slot as first-class plan steps with an explicit slot lifecycle on deactivation | The WAL-pinning foot-gun gets a named choice |
| Force Start Replication Jobs (unchecked = jobs SUSPENDED) | Start policy on every plan: orchestrated start or leave-suspended | Change-window staging is first-class |
| Trigger-capture components (-ot / -op / -oc source side, deprecated) | Not carried — log-based capture only | Legacy shed, not inherited |
| Deactivation defaults: all components selected (drop everything) | Retention-first default; destructive components opt-in with typed confirmation | Safe by default, pleading docs retired |
| Enrollment deletion always whole-channel despite table selection | Per-table enrollment removal (STR-14 symmetry) | Silent widening designed out |
| Supplemental-logging drop ignores table selection (all tables) | Never dropped by default; explicit removal per-table, capability-gated | The scope you selected is the scope you get |
| Capture time + queued transaction file deletion | Guarded destructive step with open-transaction warning; file-log residue GC'd per ack discipline | Typed confirmation, not a checkbox |

## 9. Test Plan

The stream test plan runs in four phases, each with an entry condition, its criteria set, and an exit condition. The standing rule from the README applies throughout: a criterion passes only when its procedure (section 10) has been executed with all expected results observed and evidence archived. The full CHA suite reruns on every merge touching stream, activation, or style code — phases order initial verification; regression is total.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Definition model | STR-01, STR-02, STR-10, STR-23, STR-24, STR-28, STR-29 | Unit + clean lab hub pair | Stream schema and validator implemented | All pass in CI; round-trip byte-equivalence proven |
| B | Replication styles | STR-03, STR-04, STR-05, STR-06 | Integration lab, scripted DML corpus | Phase A exit; integrate paths implemented | All pass on Postgres target; rerun per additional target class as connectors land |
| B2 | Keys | STR-19, STR-20, STR-21, STR-22 (gated) | Integration lab + key fixture set + distributed-target fixture | Phase A exit; key selection implemented; STR-22 additionally gated on the first distributed-target connector | STR-19..21 pass; hierarchy, implicit semantics, and guardrail proven; STR-22 exits with the connector that activates it |
| C | Lifecycle and activation | STR-07 (gated), STR-08, STR-09, STR-11, STR-13, STR-14, STR-15, STR-18, STR-25, STR-26, STR-27 | Integration lab under TPC-C load; state-diff fixture library | Phase B exit; planner implemented; STR-07 additionally gated on the ddl-capture design pass and implementation | All non-gated criteria pass; plan minimality and every guardrail proven; timing numbers recorded for STR-14; STR-07 exits with DDL capture |
| D | Resilience and rewind | STR-12, STR-16, STR-17 | Chaos harness; long-running-transaction generator; hub-destruction drill | Phase C exit | All pass including the full hub-loss recovery drill |

### 9.1 Methods

**Definition tests** exercise the schema validator with a fixture set of invalid definitions (empty groups, source-incapable location in a source group, pattern matching zero tables, conflicting per-table overrides) — every fixture must fail at save time with a message naming the field. Round-trip tests export a definition via CLI, re-apply it to a clean hub, and diff the resulting repository state (byte-equivalent behavior, GitOps depends on it).

**Style tests** run a scripted DML sequence (inserts, updates, deletes, key updates, multi-row transactions) through each style and audit the target against a precomputed expected state — for TimeKey, including the change-metadata columns and their ordering, and reconciling against the worked example in section 3.1. Style-override tests mix styles per table within one stream.

**Lifecycle tests** cover activation under live load (zero-downtime start verified by compare — the step-8 handshake of section 6.5 is exactly what STR-08 proves), pause/resume with checkpoint integrity, definition versioning (every change diffed and attributed), and retirement leaving no file-log residue after GC.

**Activation-plan tests** center on a state-diff fixture library: hubs and locations prepared in known partial states (missing enrollment for two tables, supplemental logging absent on one, stale jobs, existing state tables) against which computed plans are asserted step-for-step — minimality is a tested property, not a hope. Destructive-guard tests attempt every documented foot-gun (state-table recreation without confirmation, recreation combined with recovery rewind, burst-table drop mid-cycle) and assert refusal. The rewind matrix runs against a long-running-transaction generator (open transactions spanning the capture start) so the oldest-open-transaction and emit-from-now semantics are verified against ground truth, not intuition.

**Table-group tests** verify the resolution ladder end to end: fixtures with settings at all four levels assert the documented precedence per table, and the effective-settings view's provenance labels are asserted against ground truth (UI and API). Auto-assign-by-schema is tested against the many-schema fixture, including the lock (manual rename refused) and the GENERAL default.

**Naming tests** run the normalization fixture set (over-length names, spaces and symbols, non-ASCII scripts, reserved-prefix names, deliberate post-normalization collisions) through table selection, asserting each published rule, each badge text, and the collision refusal. Mapping fixtures cover both rename directions, same-base-different-schema, and one-source-to-many-targets, verified by data landing (compare per target table).

**Key tests** run against a dedicated fixture set: tables with a primary key, with only a mandatory-column unique index, with only a nullable-column unique index (must be skipped), with several competing candidates (dictionary hierarchy must decide), and with nothing usable (implicit key). Selection, provenance display, and badging are asserted per fixture. Implicit-key semantics are verified on a table seeded with genuine duplicate rows; the no-duplicate-rows guardrail is tested in both directions (clean table unlocks the fast path; dirty table is caught). Distribution-key tests inspect generated DDL on the distributed-target fixture, including the staging/target alignment invariant.

**Object-inventory sweep** (supports section 6.6): after every phase-C run, an audit enumerates all objects present on source and target and diffs against the published inventory — any undocumented object on a customer system fails the run. The no-source-objects promise is thereby tested, not asserted.

## 10. Test Procedures

### STR-01 — Invalid definitions refused at save time
**Preconditions:** Fixture set of eight invalid stream definitions (empty source group; target-only location in source group; zero-match table pattern; duplicate table with conflicting overrides; unknown field; bad style value; keyless table under standard replica without no-PK handling; cascading declared inside one stream).
**Steps:** (1) Attempt to save each via REST API and via UI. (2) Record each refusal. (3) Correct one fixture per its message; re-save.
**Expected:** All eight refused in both paths with field-level messages; corrected fixture saves; no partial definitions persisted (repository audit).
**Evidence:** Refusal captures, repository audit.

### STR-02 — Definition round-trip fidelity
**Steps:** (1) Build a maximal stream in the UI (multi-location groups, patterns, per-table overrides, all three styles represented). (2) Export via CLI. (3) Apply the export to a clean lab hub. (4) Diff both hubs' effective stream state via API; run identical DML through both and compare targets.
**Expected:** Effective-state diff empty; both targets identical after the DML run.
**Evidence:** State diff, dual compare reports.

### STR-03 — Standard replica correctness
**Steps:** (1) Run the scripted DML sequence (10k operations including key updates and multi-row transactions) through a standard-replica stream. (2) Compare target vs source; audit that deletes removed rows.
**Expected:** Compare clean; deleted keys absent on target.
**Evidence:** Compare report, delete audit.

### STR-04 — Soft delete materialization
**Steps:** (1) Same DML sequence through a soft-delete stream with configured marker columns. (2) Audit: deleted source rows present on target with markers set and timestamps plausible; non-deleted rows have markers clear; a re-insert of a previously deleted key behaves per the documented rule.
**Expected:** Every source delete is a marked target row; zero physically deleted target rows; re-insert case matches documentation.
**Evidence:** Marker audit queries, re-insert case log.

### STR-05 — TimeKey audit trail
**Steps:** (1) Same DML sequence through a TimeKey stream into a file target and a Postgres target. (2) For 20 sampled source rows, reconstruct their history from the target and verify operation types, ordering by commit position, and origin markers against the known script. (3) Verify no updates/deletes occurred on the target (append-only audit).
**Expected:** Reconstructed histories match the script exactly; targets are append-only; metadata columns match the published spec.
**Evidence:** History reconstructions, append-only audit.

### STR-06 — Per-table style mixing
**Steps:** (1) One stream, three tables, one style each. (2) Run the DML sequence touching all three. (3) Apply STR-03/04/05 audits per table.
**Expected:** Each table materializes per its own style with no bleed-through.
**Evidence:** Three per-table audits.

### STR-07 — DDL policy per stream and table *(gated: blocked until the ddl-capture design pass is complete and implemented)*
**Preconditions:** DDL capture implemented per `ddl-capture.md` (planned — README document set); until then this procedure cannot execute and its criterion stays open in the matrix.
**Steps:** (1) Stream with DDL policy adapt; one table overridden to hold-and-alert. (2) Add a column to both tables on the source under load. (3) Observe: adapted table propagates; held table alerts and queues. (4) Approve the held change; verify propagation.
**Expected:** Adapt path propagates without refresh; hold path stops that table only, alerts, and applies cleanly on approval; other tables unaffected throughout.
**Evidence:** Event log, schema diffs before/after, alert record.

### STR-08 — Zero-downtime activation
**Steps:** (1) TPC-C at full rate. (2) Activate a new stream using online refresh with SCN coordination. (3) After activation and catch-up, compare.
**Expected:** No source quiesce required; compare clean, proving the refresh/capture boundary lost and duplicated nothing.
**Evidence:** Activation timeline, compare report.

### STR-09 — Pause, resume, retire
**Steps:** (1) Pause a running stream under load; verify checkpoints held and no data movement (wire quiet). (2) Resume; drain; compare. (3) Retire the stream; after GC interval, audit hub file store and repository.
**Expected:** Clean resume with zero loss/duplication; retirement leaves zero stream files post-GC and a retained, read-only definition with full version history.
**Evidence:** Wire capture during pause, compare report, post-retirement audits.

### STR-10 — Definition versioning and attribution
**Steps:** (1) Make three definition changes: one via UI, one via API, one via GitOps apply. (2) Inspect the version history.
**Expected:** Three versions, each with actor, timestamp, and field-level diff; GitOps change attributed to its commit reference.
**Evidence:** Version history export.

### STR-11 — Plan minimality and auto-scope
**Preconditions:** Running 20-table stream; state-diff fixture: one new table added to the definition.
**Steps:** (1) Request activation; capture the computed plan. (2) Assert the plan contains only: jobs re-registration, enrollment for the new table, supplemental logging for the new table on the source, and nothing for the 19 unchanged tables or the target beyond job registration. (3) Apply; verify the new table replicates; compare.
**Expected:** Plan is exactly the minimal step set; unchanged tables untouched (enrollment timestamps unchanged); compare clean including the new table.
**Evidence:** Plan capture, enrollment timestamp audit, compare report.

### STR-12 — State-table recreation guard and ordering enforcement
**Steps:** (1) Request a plan including state-table recreation without the destructive confirmation; assert refusal. (2) Repeat with typed confirmation; assert the plan displays the exact loss warning and applies. (3) Request a plan combining state-table recreation with recovery rewind to integrate sequence.
**Expected:** (1) refused; (2) applied only after typed confirmation, warning text matches documentation verbatim; (3) planner rejects the combination as invalid with the documented explanation.
**Evidence:** Three plan transcripts.

### STR-13 — Burst-table protection mid-cycle
**Preconditions:** Burst integrate mid-cycle (changes staged, not yet merged — held via test hook).
**Steps:** (1) Request a plan that would drop burst tables. (2) Observe refusal/wait behavior. (3) Release the cycle; re-plan; apply. (4) Repeat step 1 with the force flag.
**Expected:** (2) plan refuses or waits for drain per configuration, stating why; (3) proceeds cleanly after drain with compare clean; (4) force path states the recoverability consequence and requires confirmation.
**Evidence:** Plan transcripts, compare report.

### STR-14 — Incremental enrollment
**Preconditions:** 200-table lab stream, all enrolled; definition change touching 3 tables.
**Steps:** (1) Plan and apply; time the enrollment step; record which tables were re-enrolled. (2) For contrast, run a forced full re-enrollment and time it.
**Expected:** Only the 3 changed tables re-enrolled; incremental time a small fraction of the full run (both recorded as the published numbers).
**Evidence:** Enrollment audit, timing pair.

### STR-15 — Supplemental logging idempotence, parallelism, deactivation
**Steps:** (1) First activation on a 2-source stream: verify logging enabled at documented granularity per table, sources processed in parallel (overlapping timestamps). (2) Re-activate with no changes: assert the plan contains no supplemental-logging step. (3) Deactivate the stream; audit source logging state.
**Expected:** Granularity per spec; parallel execution observed; no-op plan on unchanged re-activation; logging fully intact after deactivation.
**Evidence:** Source logging audits before/after, plan captures, timing overlap.

### STR-16 — Capture start and emit time matrix
**Preconditions:** Long-running-transaction generator: transaction T1 opened before activation, committed after; change C1 made and committed ~55s before "now"; change C2 committed after "now."
**Steps:** (1) Activate with capture-start = oldest open transaction, emit = committed-from-now. (2) Verify T1's changes replicate in full, C1 is not emitted, C2 is. (3) Separately, activate with custom rewind to a recorded SCN and emit-from-rewind; verify the boundary row-exactly.
**Expected:** All three boundary behaviors match the specification exactly; log-availability precheck passes/fails correctly when logs are aged out (negative sub-case).
**Evidence:** Boundary row audits per case, precheck negative result.

### STR-17 — Recovery rewind after hub loss
**Steps:** (1) Run a stream under load; destroy the hub (delete container and file store). (2) Build a fresh hub from the repository backup; use recovery rewind to the target's integrate sequence (exercising the renamed-stream option against a renamed fixture). (3) Resume; drain; compare; duplicate-check target keys.
**Expected:** Capture resumes from the target-recorded position; compare clean; zero duplicates — loss-less hub failover as specified, without state-table recreation.
**Evidence:** Rewind transcript, compare and duplicate-check results.

### STR-18 — Post-activation refresh creation policies
**Preconditions:** Target fixtures: one table missing, one with mismatched layout, one with an extra customer column and index.
**Steps:** For each policy — create-missing; create/alter-mismatched; create/alter with keep-existing-structure; recreate-all with keep-old-rows — (1) chain the refresh from activation, (2) audit target DDL and data afterward.
**Expected:** Missing table created only under the policies that promise it; mismatched table altered/recreated exactly per policy; keep-existing-structure preserves the extra column and index and never shrinks; keep-old-rows preserves prior data through recreation; bulk path verified by compare in every run.
**Evidence:** DDL diffs per policy, data audits, compare reports.

### STR-19 — Key selection hierarchy and provenance display
**Preconditions:** Key fixture set: table with PK; table with mandatory-column unique index only; table with nullable-column unique index only; table with PK plus two unique indexes; table with no candidates.
**Steps:** (1) Add all five to a stream; capture the per-table key display (UI and API). (2) Assert selection per hierarchy: PK chosen where present; mandatory unique chosen next; nullable unique skipped (its table falls to implicit); competing-candidates table resolves to the PK; last table gets the implicit key with badge. (3) Verify the wizard summary counts implicit-key tables correctly.
**Expected:** Every selection, provenance label, and badge matches the hierarchy specification; API and UI agree.
**Evidence:** Per-fixture display captures.

### STR-20 — Implicit-key semantics with real duplicates
**Preconditions:** Implicit-key table seeded with 3 identical rows plus distinct rows; standard-replica stream.
**Steps:** (1) On the source, update one distinct row; verify the target apply executed as delete+insert (statement audit). (2) Delete exactly one of the 3 identical source rows. (3) Audit the target: exactly one of the identical rows removed. (4) Compare.
**Expected:** Update materialized as key-update pair; single-row-limited delete removed one row, not three; compare clean.
**Evidence:** Target statement audit, row counts before/after, compare report.

### STR-21 — No-duplicate-rows guardrail, both directions
**Steps:** (1) On the duplicate-seeded table, set the no-duplicate-rows flag with the check enabled; assert refusal naming the duplicate key values found. (2) On a clean implicit-key table, set the flag; verify acceptance and that subsequent updates use the direct path (statement audit shows no delete+insert). (3) Set the flag with the check policy at warn on the dirty table; verify the warning and its audit entry.
**Expected:** Refuse, accept-with-fast-path, and warn behaviors each match policy; the fast path is observably different in the statement audit.
**Evidence:** Guardrail outputs, statement audits.

### STR-22 — Distribution keys and the staging alignment invariant *(gated: runs when the first distributed-target connector lands)*
**Preconditions:** Distributed-target fixture (lab Greenplum or equivalent); Redshift-class validation fixture. Gated on the first distributed-target connector (roadmap — see 4.4 scope note); until then the staging-alignment invariant is covered at unit level in the table-creation code.
**Steps:** (1) Create tables via burst integrate: one with an explicit distribution key, one implicit (verify derivation from the first replication-key column, honoring an avoid-pattern fixture and the column limit). (2) Inspect generated DDL: target and its staging table share the distribution key; target has the replication-key index (uniqueness per provenance/flag), staging has none. (3) Attempt a multi-column distribution key on the Redshift-class location.
**Expected:** Derivations and DDL match specification exactly; the staging/target alignment holds for every table; the Redshift multi-column attempt is refused at definition time with the capability-matrix message.
**Evidence:** Generated DDL captures, refusal message.

### STR-23 — Table groups: assignment, resolution, provenance
**Preconditions:** Many-schema fixture (two source schemas, 20 tables); settings placed at stream, group, and table level with deliberate conflicts.
**Steps:** (1) Select tables with auto-assign-by-schema; assert group derivation, uppercase naming, and that manual rename of an auto-assigned group is refused. (2) Add ungrouped tables; assert GENERAL membership. (3) Set schema mappings at group level (the GROUP_A/GROUP_B example); set a conflicting override on one table. (4) Query the effective-settings view (UI and API) for five tables spanning the cases; assert each resolved value and its provenance label against the documented ladder. (5) Run the stream; verify rows land in the correct target schemas; compare. (6) Re-group one table in the editor; assert a versioned, attributed definition change.
**Expected:** Assignment rules exact; resolution follows table > group > stream precedence; provenance labels correct in both surfaces; data lands per mapping (compare clean); re-grouping versioned.
**Evidence:** Effective-settings captures, target schema audit, compare report, version history entry.

### STR-24 — Identity derivation, badges, and mapping cases
**Preconditions:** Normalization fixture set: a 34-character table name; names with spaces, symbols, and Chinese characters; a reserved-prefix name; two names that collide after normalization. Mapping fixtures: rename a→b; same base name in two schemas; one source table to two targets.
**Steps:** (1) Add the normalization fixtures via table selection; assert each derived identity against the published rules and each badge's text (UI and API). (2) Assert the collision pair is refused at definition time naming both tables. (3) Configure the three mapping fixtures (rename via target-side base name, then equivalently via source-side; schema pair; fan-out with per-identity styles). (4) Run the stream; audit target objects and data landing per mapping; compare per target table. (5) Rename the physical source table of one fixture (DDL) and verify the identity — and all its settings and state — persist per the DDL policy.
**Expected:** Every derivation and badge matches the published rules; collision refused; all mapping cases land data correctly (compares clean); identity survives the physical rename with settings and state intact.
**Evidence:** Derivation/badge captures, refusal message, target audits and compare reports, post-rename state check.

### STR-25 — Detail page: panes, jobs operations, suspension modes
**Preconditions:** Live stream under TPC-C load; Playwright harness; error-seeding hook.
**Steps:** (1) Drive the summary pane: location links, table-count link, direction arrow per topology fixture; open effective settings and diff the panel against the API's resolved values. (2) Seed known change volumes across ranges; assert both graphs against the metrics API series (totals per interval; latency band vs measured deltas). (3) Jobs pane: assert live state updates; seed an error, dismiss it, verify it leaves the pane AND an acknowledgment event records actor and error; bulk-select three jobs (shift-range) and suspend, then start. (4) Graceful suspension under load: drain dialog until cycle boundary; wire quiet afterward; resume; compare clean. (5) Force suspension mid-cycle: immediate stop; resume; compare clean and zero duplicates (checkpoint safety observed, not assumed).
**Expected:** Every pane matches its API source exactly; dismissal is audited; graceful waits for the boundary; force costs only redone work — both compares clean.
**Evidence:** Panel-vs-API diffs, acknowledgment event, drain timeline, two compare reports with duplicate checks.

### STR-26 — Stream management menu
**Steps:** (1) Duplicate the stream; assert the new draft's definition diffs empty against the source while carrying zero jobs, state, or history, and the duplicate event names its source. (2) Rename the stream under running replication; assert a versioned event, uninterrupted jobs, intact internal references, and a clean compare afterward. (3) Export the definition and re-apply to a clean hub (STR-02 alignment). (4) Add an existing location to the target group; assert the computed plan touches only the new location and the stream extends without table/setting re-declaration; compare includes the new target. (5) Deactivate via plan; audit the default plan first: state tables, supplemental logging, populated error/history tables, and the PG slot choice all retained/explicit, destructive components absent unless opted in; apply; audit: jobs stopped, supplemental logging fully intact on sources, state tables retained; re-activate and assert resume (not rebuild) with a clean compare. (6) Request a table-scoped deactivation plan for 2 of the stream's tables; assert every step (enrollment removal included) is scoped to exactly those 2 tables and no component silently widens to the whole stream; attempt the destructive extras (state tables, capture position) and assert each requires its typed confirmation with the loss named.
**Expected:** Every menu operation behaves per specification; deactivation defaults are retention-first with honest per-table scope; destructive teardown is opt-in and confirmed; re-activation resumes from retained positions.
**Evidence:** Definition diffs, rename event and post-rename compare, plan captures, source logging audit, resume timeline and compare.

### STR-27 — Creation wizard end to end
**Preconditions:** Clean lab hub; existing eligible and ineligible locations (a target-only class among them); the many-schema and key fixture sets; Playwright harness.
**Steps:** (1) Walk the wizard: assert inline name validation (an identity-rule-violating name refused as typed); assert the source picker excludes the target-only class; create one location inline and verify the validation suite ran; confirm and assert SOURCE/TARGET groups exist and are renamable. (2) Select Mode 3 (CDC + scheduled compare) and a style; on a second run select Mode 2 with a SELECT-only location and assert capture setup is skipped. (3) In the tables step, assert auto-group assignment, normalization badges, the implicit-key summary line, and the DDL policy selector. (4) Save-and-exit mid-wizard; assert a resumable validated draft exists and zero runtime objects were created (object-inventory sweep); resume and finish. (5) At completion, assert the displayed plan equals the planner's API output for the same definition (STR-11 minimality) with the chained refresh included and the equivalent CLI shown; approve; assert landing on the detail page with the stream green and compare clean. (5b) Rerun completion on a second stream choosing *leave jobs suspended*; assert every object was created, capture and integrate sit SUSPENDED, and a later manual start proceeds in the 6.5 order to a clean compare. (6) Use *export what you built*; apply the export to a clean hub via CLI; assert equivalent behavior (STR-02 alignment).
**Expected:** Every step's validation and surface behaves per sections 2, 4, 5.1, and 6; the draft is inert until applied; the wizard's plan is the planner's plan; the export replays.
**Evidence:** Per-step captures, inventory sweep results, plan-vs-API diff (empty), compare report, replay diff.

### STR-28 — Export classified-data matrix
**Preconditions:** Stream with two locations: one on an external secret reference, one with stored (envelope-encrypted) credentials carrying canary values; a second lab hub; a user without the elevated export permission.
**Steps:** (1) Export in each mode — secret-references (default), redacted, transport-key — and sweep every export file for the canary strings. (2) Import the transport-key export on the second hub with the key; verify working connections. (3) Import the same file without the key; verify it degrades to redacted with the exact checklist. (4) Attempt a transport-key export as the unprivileged user; verify refusal. (5) Confirm every export produced an audit event naming scope and mode; confirm no obfuscated-values mode exists anywhere in UI or API.
**Expected:** Zero canary hits in any export file; keyed import connects, keyless degrades with checklist; permission enforced; events present; the foot-gun mode is absent.
**Evidence:** Canary sweeps (empty), both import outcomes, refusal capture, event records, API surface audit.

### STR-29 — Import plan, collisions, and redacted repair
**Preconditions:** Target hub already containing a stream and locations with colliding names; a redacted export and a secret-reference export of a multi-location stream.
**Steps:** (1) Import the secret-reference export; verify the preview plan enumerates every object to be created or changed before anything is applied. (2) Resolve the collision as import-under-new-name; verify the renamed stream references the existing locations (zero suffixed location copies created — object inventory audit). (3) Re-import choosing replace; verify it lands as a versioned definition change with the prior version in history. (4) Import the redacted export; verify the post-import checklist names exactly the credential-less objects, activation is refused by validation until credentials are supplied, and succeeds after.
**Expected:** Plan-preview before apply; no orphan location clones under rename; replace is versioned, not destructive; the redacted gap is a checklist and a validation block, never a runtime surprise.
**Evidence:** Preview captures, object inventory diff, version history, refusal-then-success validation transcripts.

## 11. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| STR-01 | Invalid stream definitions are refused at save time with field-level messages; no partial definitions persist |
| STR-02 | A CLI-exported definition applied to a clean hub yields byte-equivalent effective behavior (state diff empty; identical DML produces identical targets) |
| STR-03 | Standard replica mirrors the scripted DML exactly (compare-verified; deletes physically applied) |
| STR-04 | Soft delete marks every source delete on the target with configured columns; zero physical target deletes; documented re-insert behavior |
| STR-05 | TimeKey produces a correct, append-only, metadata-complete audit trail matching the published spec |
| STR-06 | Mixed per-table styles within one stream materialize independently with no bleed-through |
| STR-07 | *(gated on the ddl-capture design pass)* DDL policies (adapt / hold-and-alert) behave per configuration at stream and table level; held changes apply cleanly on approval |
| STR-08 | Zero-downtime activation under full load: compare clean across the refresh/capture boundary |
| STR-09 | Pause holds checkpoints with zero data movement; resume is loss/duplicate-free; retirement leaves no file residue and a retained definition history |
| STR-10 | Every definition change is versioned with actor, timestamp, and diff across UI, API, and GitOps paths |
| STR-11 | Activation plans are minimal and auto-scoped: a change touching N tables produces steps for exactly those tables and affected locations |
| STR-12 | State-table recreation requires typed destructive confirmation; a plan combining recreation with recovery rewind is rejected by the planner |
| STR-13 | Burst tables are never dropped mid-cycle without explicit force; the default plan waits for cycle drain |
| STR-14 | Enrollment is per-table incremental; a 3-table change on a 200-table stream re-enrolls exactly 3 tables |
| STR-15 | Supplemental logging is granular per spec, parallel across locations, no-op on unchanged re-activation, and never dropped on deactivation; on PostgreSQL sources the publication and replication slot are plan-created, inventoried, and offered an explicit retain-or-drop choice on deactivation |
| STR-16 | Capture-start and emit-time combinations behave exactly as specified against long-running and boundary-committed transactions, with log-availability prechecked |
| STR-17 | A destroyed hub is rebuilt and resumes via recovery rewind to the target integrate sequence with zero loss and zero duplicates |
| STR-18 | Post-activation refresh honors every table-creation policy exactly (create-missing, alter/recreate, keep-structure, keep-old-rows), compare-verified |
| STR-19 | Replication key selection follows the hierarchy exactly across the key fixture set, with provenance and implicit-key badges displayed identically in UI and API |
| STR-20 | Implicit-key tables execute updates as delete+insert and deletes as single-row-limited statements; one of N identical rows is removed, compare-verified |
| STR-21 | The no-duplicate-rows guardrail refuses, warns, or accepts per policy; the accepted fast path is observable in the target statement audit |
| STR-22 | *(gated on the first distributed-target connector)* Distribution keys derive and validate per spec; staging and target tables always share the distribution key; per-target limits enforced at definition time |
| STR-23 | Table groups assign per spec (auto-by-schema, GENERAL default, one group per table); the settings ladder resolves as documented with correct provenance in UI and API; group mappings land data correctly |
| STR-24 | Identity derivation follows the published normalization rules with accurate badges; collisions refused at definition time; rename, schema, and fan-out mappings land data correctly; identity persists across physical renames |
| STR-25 | The detail page's panes match their API sources exactly; error dismissal is an audited acknowledgment; graceful suspension drains to the cycle boundary and force suspension is checkpoint-safe, both compare-clean |
| STR-26 | Duplicate, rename, export, add-location, and plan-based deactivation behave per spec; deactivation defaults are retention-first, its scope never silently widens, destructive components are opt-in with typed confirmation, and re-activation resumes from retained positions |
| STR-27 | The creation wizard validates at every step (names inline, locations by capability, keys and naming badged), leaves inert resumable drafts, completes through the computed activation plan, and its export replays to equivalent behavior |
| STR-28 | Every export mode keeps secret material out of files (canary-proven); transport-key round-trips work keyed and degrade to redacted keyless; the permission is enforced, every export is evented, and no obfuscated-values mode exists |
| STR-29 | Imports preview as plans before applying; name collisions never clone locations into orphans; replace is a versioned change; redacted imports yield an exact checklist with activation blocked until credentials are supplied |

## 12. Open Questions

Whether group-level settings should be overridable per location within a group (integrate method per target in a broadcast) or forced uniform needs a decision before the schema freezes. The soft-delete re-insert rule (revive vs new-row) defaults per target class need field input. Whether TimeKey on relational targets should offer optional partitioning DDL generation (by commit date) is a v1.x candidate. Source key changes (a PK added, dropped, or altered on a live table) need a defined policy under each DDL mode — re-derive the replication key automatically versus hold-and-alert — before the DDL-capture design pass; automatic re-derivation of the key that identifies rows is exactly the kind of silent behavior this section exists to avoid. The identity maximum length and the transliteration table for non-Latin scripts need fixing before the schema freezes — both become published, versioned constants once shipped.
