# Tables — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design; the fleet-wide table surface and table-scoped operations
**Vocabulary note:** written in the locked naming (stream, connection — naming.md); cross-referenced spec files keep their pre-sweep names until the rename sweep.

---

## 1. Purpose and Positioning

The table is where replication meets the business — nobody's SLA mentions a stream, but everyone's mentions ORDERS. The **Tables view** is the hub-wide answer to table-first questions: every table across every stream (or filtered to one), with its identity, its physical names per side, its group, its change volume, and — the column that matters — *when was this table last verified, and what was the verdict?* Table structure concepts (identity vs physical names, table groups, the table set) are owned by the stream spec §2.4–2.5 and referenced here, not restated; this document owns the view, the per-table status model, definition drift handling, and the table-scoped operations.

## 2. The Tables View

**Columns.** Table identity (the stream-level name); stream; **name in source** and **name in target** — the physical names with schema prefix where the DBMS has schemas, with a per-side connection selector (default *Automatic*: show all, and for tables on multiple connections, show the most recent operation's connection); table group; **recent refresh** and **recent compare** (the status model below); and an **average-changes sparkline** over the selected graph range — which requires per-table change-volume series in the metrics store, a requirement recorded here because the stream detail page (stream spec §7.2) only demanded stream-level series. Optional columns toggle via a column picker. Filters: stream selector, table-group selector, and search-as-you-type across identities and physical names. Every column sorts (names alphabetically, statuses by operation time, changes by volume). Like every view, this page is documented REST calls rendered — the fleet table list is one API query anyone can script.

**Name display under divergence.** When a table's physical names differ across connections, the cell shows the honest minimum: the common name when only schemas differ, and a **“varies” marker expanding to the per-connection list** when the names genuinely diverge — replacing HVR's `table1+` suffix convention, which is compact but requires knowing the convention. The identity/physical badges of stream spec §2.5 appear here exactly as they do at import time: one rule, every surface.

**The per-table status model.** Recent refresh and recent compare each show: state, rows processed, and when. States, adopted from HVR with its most honest one kept proudly: **PENDING** (event created, this table not started), **BUSY** (in progress), **BUSY/DIFFERENT** (in progress and a difference already found — why wait for the end to start worrying), **DONE/IDENTICAL**, **DONE/DIFFERENT**, and **DONE/INCONCLUSIVE** — the online-compare case where differences were seen but could not be attributed to drift versus in-flight change before the run ended. Inconclusive maps precisely to our double-compare heuristic labeling (compare spec §4.1) and to the in-flight re-check window closing without resolution: the platform says *"could not decide"* rather than guessing in either direction, and the state links to the report explaining what was unresolved and why. NONE means no event has ever touched the table.

## 3. The Table Detail Page

One table, everything about it. The header carries the naming block — identity, physical name per connection (source and target), table group — with change controls that route to the right machinery: **changing a physical-name mapping** is the cheap case, an ordinary versioned definition edit (identity persists across physical renames — the stream spec's STR-24 property, so replication is unaffected); **changing the table group** is a settings-inheritance move with the provenance ladder showing what changes. **Renaming the identity itself** is the hard case, and it gets a designed answer rather than HVR's dialog: the identity is what file-log frames, state bookkeeping, and settings all key on, so an identity rename is a **plan** that applies the definition change immediately while the runtime maintains an **alias window** — the old identity remains resolvable until every in-flight frame written before the rename point has been applied everywhere, at which point the alias retires automatically, with an event marking it. No drain-the-stream prerequisite, no ambiguity window; the alias's existence and retirement are both visible.

**The columns tab** is the published type-mapping table made concrete, per column: name, **definition data type**, the key badge (with the implicit-key marker where the key was inferred — §4.2 of the stream spec, same badge everywhere), the **actual type in the source**, and the **actual type in each target** — the Oracle `NUMBER` that lands as SQL Server `DECIMAL`, shown on the row where the question arises instead of in an appendix. Per-column structured settings appear with click-through to the settings panel filtered to that column, provenance intact. Where context-conditional settings exist (a column that only materializes under a named context — the refresh/compare contexts machinery), a **context preview** toggle renders the effective structure with the context enabled, so "what does this table look like when context X is on" is a click, not a mental simulation.

**Column editing** is definition editing with the ripple made visible: add column (before/after — ordering is definitional and preserved), edit (name, type, attributes, key membership), delete from definition. Every edit is the ordinary versioned change, and edits with physical consequences preview their **ripple plan** — the target alter under the creation policy, the capture-registration refresh — before applying; a change that breaks the stream's constraints (removing the last key column under a keyed style) is a validation refusal with the reason.

**The history tabs** — Compare History and Refresh History — are the per-table view of the event ledger: every compare and refresh event that touched this table, with event state, the per-table state (the same model as §2, INCONCLUSIVE included), rows selected on each side, duration, and **speed (rows/second)** — the column that turns history into capacity data. Each row links to its Event Details (artifacts, report) and its connections' detail pages. Nothing here is a new store: it is one filtered ledger query, which means it is also one API call and one CLI command.

### 3.1 Column names are per side — source name ≠ target name

A column, like a table, has an **identity** and a **physical name per side**, and the two need not agree. `MFG.WORKORDERS.WORKORDER_ID` may land on Databricks as `workorder_id`, on Snowflake as `WORKORDER_ID`, and in a curated Postgres mart as `work_order_key` — all the same column, all at once, in the same stream. The mapping is directional and independent in both directions: renaming the source column (out-of-band DDL, or an adopted drift) does not rename the target column, and renaming the target column never touches the source catalogue. The platform is a reader of the source and a writer of the target; it owns neither name.

**What holds the relationship together is the identity, not the string.** Frames on the file log, per-column settings, key membership, compare column pairing, and the metrics series all key on the column identity. That is what makes divergent names cheap: capture reads `WORKORDER_ID`, the frame carries the identity, apply writes whatever the target side's physical name is. A rename on either side is a versioned definition edit against an unchanged identity — the same STR-24 property tables already have, applied one level down.

**Defaults, so the common case needs no decision.** On import, the target physical name defaults from the source name under the target's naming convention (case-folding per DBMS — lower for Postgres/Databricks/Parquet, as-is for Snowflake, plus reserved-word and length handling), so the vast majority of columns are mapped without anyone typing anything. Divergence is opt-in and always visible: the Tables detail grid shows **Column** (source physical name) and **Target column** side by side, and a column whose two names differ reads as a rename in the Replication rules panel rather than hiding in a settings file.

**Editing.** The column editor takes both names, both types, nullability, key membership, and notes in one dialog, because those are the fields that answer "what is this column, and what does it become". Both names are free text; validation is per side — the source name must resolve in the source catalogue (a name that does not is drift, and routes to §4), and the target name must be legal for the target DBMS and unique within the target table after mapping. A change to either name is staged as a plan with its ripple: a target rename implies a target `ALTER … RENAME COLUMN` under the creation policy (or a recreate where the target has no rename), a source rename implies a capture-registration refresh; neither implies a refresh of the data.

**Collisions and the honest refusals.** Two source columns mapping to one target name is a validation refusal naming both. A target rename that collides with a column the creation policy would add (`OP_TYPE`, `OP_TS`, slice or partition helpers) is a refusal, not a silent suffix. A rename of a key column carries the key with it — the apply's matching predicate is rebuilt from the identity, so the key follows the column rather than the string.

**Where names must not diverge.** Compare pairs columns by identity, so divergent names compare correctly and the report prints both — `WORKORDER_ID / work_order_key` — because an operator reading a difference report is holding two databases open, not one. Definition export/import carries both names; a table definition moved to another stream keeps its source name and re-defaults its target name only when the destination's target DBMS differs.

## 4. Definition Drift — check and adopt

The registered table definition (what the stream believes) and the actual database table (what exists) can diverge — out-of-band DDL on either side, a hold-and-alert DDL policy queuing a change, a target someone "fixed" by hand. Two operations handle it, both new to our spec set via this page:

**Check definition against actual.** A validation that compares the registered definition with the live catalog on source or target, per table or in bulk, producing a **field-level drift report**: column added/dropped/retyped, length changes, key changes — the same discrepancy vocabulary as structure-first compare (CMP-12), applied at definition level without touching row data. Clean tables say clean; drifted tables name exactly what drifted. Scheduled drift checks are just Mode-3-style scheduled validations, and a drift finding raises the standard alert with the report linked.

**Redefine from actual (adopt).** When reality should win, the registered definition updates *from* the live catalog — and consistent with everything else in this platform, **adoption is a plan**: the computed definition change (versioned, attributed, field-level diff — the ordinary stream-spec change machinery), plus the ripple it implies — target alters where the creation policy allows, capture registration refresh for the affected tables, and validation refusals where the adopted structure breaks the stream's constraints (a dropped key column under a keyed style is a refusal with the reason, not a silent acceptance). The plan preview shows all of it before anything applies; the applied adoption is one event carrying the diff.

Together these close the DDL loop for the hold-and-alert policy: the alert fires (DDL policy), the check names the drift, the adopt plan applies it deliberately — the manual complement to the adapt policy's automatic path.

## 5. Table-Scoped Operations

The view's operations menu, with the shift-click range selection the jobs pane already established: **add tables** (to a stream, from a connection — the wizard's step-4 surfaces apply: badges, key summary, group auto-assign); **delete tables** (from a stream — a plan with the state-implications named); **compare / refresh / activate / deactivate** scoped to the selection (the stream spec §6.7 launch-point rule: the selection *is* the scope pre-fill; a pinned stream enables the operations that need one); **create/alter target tables** (creation-policy engine); **change table group**; **import/export table definitions** — the table-level subset of the definition format, same round-trip guarantees (STR-02's format, scoped); and the two ergonomic couriers, **copy table names** and **copy names-in-source**, which exist because the next dialog (an activation scope, a filter box) wants exactly that list — small, but the kind of small that operators remember.

The start-page pointer HVR ends with is our creation wizard's front door (stream spec §5.1) — the landing surface for an empty hub is the wizard, not a separate page.

## 6. HVR Parity Matrix

| HVR tables concept | This platform | Delta |
|---|---|---|
| Tables page: all tables across channels, filter/search/sort | Same view, one API query underneath | Kept; scriptable |
| TABLE vs BASENAME columns | Identity vs physical names (stream spec §2.5), same badges everywhere | Kept; one rule, every surface |
| Name-in-source/target with location selector, Automatic default | Same, per-connection selector | Kept |
| `table1+` suffix for divergent names | "Varies" marker expanding to the per-connection list | Convention replaced by disclosure |
| Recent refresh/compare states incl. BUSY/DIFFERENT | Same state set, linked to reports | Kept — early warning preserved |
| DONE/INCONCLUSIVE (online compare undecidable) | Kept and celebrated: maps to the double-compare heuristic label and unresolved in-flight windows, always linked to the explaining report | Their honest state, made first-class |
| AVG CHANGES sparkline per table | Per-table change series in the metrics store | Kept; series requirement recorded |
| Check Definition Against Actual Source/Target | Definition drift check: field-level drift report, schedulable, alert-linked | Kept, made a validation class |
| Redefine Table From Actual | Adopt-from-actual as a plan: versioned diff + computed ripple + constraint refusals | Kept; adoption is deliberate |
| Import/export table definitions (JSON) | Table-level subset of the one definition format | Kept; one format |
| Copy table names / names-in-source | Same couriers | Kept — operators remember small things |
| Add/delete tables, group change, scoped compare/refresh/activate | Same menu; selection pre-fills scope (§6.7 rule); delete is a plan | Kept, plan-governed |
| Show Start Page | The creation wizard is the landing surface | Folded |
| Table Details header with rename dialog (table + base names) | Physical-name remap = versioned edit; identity rename = plan with an automatic alias window, no drain required | The hard case designed, not dialoged |
| Columns tab: definition type, KEY, actual type in source/target | Same grid — the published type-mapping table rendered per column, with per-column settings click-through and provenance | Kept; the appendix moved to the row |
| Context column preview (extra_col appears when context enabled) | Context preview toggle rendering effective structure per named context | Kept |
| Add/edit/delete column with before/after placement | Versioned definition edits with visible ripple plans and constraint refusals; ordering definitional | Kept, plan-governed |
| Column base name per location (name in source / name in target) | Column identity + physical name per side, defaulted from the source name under the target's naming convention, editable in either direction, both shown in the grid (§3.1) | Kept; divergence disclosed on the row, not in a settings file |
| Compare/Refresh History tabs with duration and speed | Per-table filtered ledger query with rows/side, duration, rows/sec, event and connection links | Kept; one query, also an API call |

## 7. Test Plan

Phased; standing rule applies. TBL procedures reuse the Playwright harness, the metrics store, and the drift fixtures; the full suite reruns on merges touching the tables view, definition validation, or the adopt planner.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | View correctness | TBL-01 | Lab hub, multi-stream fixture, Playwright | Metrics per-table series available | Every column, filter, sort, and state verified against API/ground truth |
| B | Drift and operations | TBL-02, TBL-03, TBL-04, TBL-05 | Lab + out-of-band DDL fixtures | Phase A exit; adopt planner implemented | Drift check exact, adoption plan-governed, detail page and rename semantics proven, operations parity proven |

## 8. Test Procedures

### TBL-01 — View correctness, states, and the inconclusive case
**Steps:** (1) Fixture: three streams, overlapping tables, one table with divergent physical names across two source connections, groups assigned. Drive the view via Playwright; diff every column against the API's values; exercise filters, search, sorts, and the column picker. (2) Verify the divergent-name cell shows the "varies" marker expanding to the exact per-connection list; verify normalization badges match the import-time badges. (3) Run a compare over a seeded-drift table and capture the state progression PENDING → BUSY → BUSY/DIFFERENT → DONE/DIFFERENT; run a clean table to DONE/IDENTICAL. (4) On a no-capture stream under a scripted change driver, run the double compare with a mutation timed between passes; assert the table lands DONE/INCONCLUSIVE with the state linking to a report that names the unresolved rows. (5) Seed known per-table change volumes; assert each sparkline against the metrics API series.
**Expected:** View equals API everywhere; divergence disclosed, not encoded; the full state progression observed including an honest INCONCLUSIVE with its explanation; sparklines exact.
**Evidence:** View-vs-API diffs (empty), state timeline captures, inconclusive report linkage, sparkline-vs-series comparison.

### TBL-02 — Definition drift check
**Steps:** (1) Baseline: bulk drift check across a clean 20-table stream; assert zero findings. (2) Apply out-of-band DDL: add a column on one source table, drop a column on one target table, widen a type on a third, alter a key on a fourth. (3) Re-run the check per table and in bulk; diff findings against the seeded changes — field-level, side-attributed, nothing extra. (4) Schedule the check on the virtual clock; assert the next cycle raises the drift alert linked to the report.
**Expected:** Zero false positives on clean; seeded drift reported exactly (field, side, nature); scheduled path alerts within one cycle.
**Evidence:** Clean report, findings-vs-seed diff (empty), alert-report linkage.

### TBL-03 — Adopt-from-actual as a plan
**Steps:** (1) From TBL-02's added-column drift, request adopt-from-source; assert the plan preview shows the versioned definition diff plus the computed ripple (target alter step under the creation policy, registration refresh for the table) and nothing else. (2) Apply; assert one event carrying the diff, the target altered, capture registration refreshed, and replication of the new column verified by compare. (3) Request adoption of the dropped-key-column drift on a keyed-style table; assert a validation refusal naming the constraint. (4) Verify adoption respects scope: a one-table adopt touches no other table's definition or objects (inventory audit).
**Expected:** Adoption previews complete and minimal, applies as one versioned event with working ripple, refuses constraint-breaking structures with reasons, never widens scope.
**Evidence:** Plan captures, adoption event with diff, post-adopt compare, refusal message, inventory audit.

### TBL-04 — Table-scoped operations parity
**Steps:** (1) Shift-select five tables; run scoped compare and scoped refresh; assert the launched plans/events are scoped to exactly the selection (§6.7 alignment). (2) Delete two tables via the menu; assert a plan naming the state implications, and post-apply, the stream compares clean on the remainder. (3) Export three tables' definitions; import into a second stream on a clean hub; assert round-trip equivalence (STR-02 subset). (4) Use both copy-names couriers and paste into an activation scope filter; assert the lists match the selection in the expected form. (5) Repeat the core operations via CLI; assert equivalence (parity rule).
**Expected:** Selection is scope, everywhere; delete is plan-governed and clean; the definition subset round-trips; couriers exact; UI/CLI equivalent.
**Evidence:** Scope captures per operation, delete plan and post-compare, round-trip diff (empty), pasted-list comparison, CLI transcripts.

### TBL-05 — Table detail page: columns, renames, edits, history
**Steps:** (1) Columns tab: on a heterogeneous stream (Oracle source → SQL Server + Snowflake targets), diff every row of the grid against ground truth — definition type from the registered definition, actual types from the live catalogs, mappings against the published type-mapping table, key and implicit-key badges against the stream spec's display; click through a per-column setting and assert the filtered settings panel with provenance. (2) Context preview: define a context-conditional column; toggle the preview; assert the effective structure with and without the context matches the settings resolution. (3) Physical-name remap under running replication: change a target physical name (with the corresponding target object rename in the same plan); assert a versioned edit, uninterrupted replication, and a clean compare. (4) Identity rename under full TPC-C load: apply the rename plan; assert the alias window exists (old identity resolvable, frames written pre-rename apply correctly), replication never pauses, the alias retires automatically once pre-rename frames drain, retirement is evented, and compare is clean end to end. (5) Column edits: add a column (before-placement), edit a type within mapping compatibility, then attempt to delete the last key column of a keyed-style table; assert the first two preview and apply their ripple plans (target alter observed, registration refreshed, new column replicates) and the third refuses with the constraint named. (6) History tabs: after a scripted sequence of three compares and two refreshes, diff both tabs against the event ledger — states, per-side rows, duration, rows/sec — and verify the event and connection links resolve.
**Expected:** The grid is the type-mapping table, verified per cell; both rename classes behave per design with the alias window observable and self-retiring; edits are plan-governed with correct refusals; history equals the ledger.
**Evidence:** Grid-vs-ground-truth diffs (empty), rename timelines with alias events, compare reports, ripple plan captures, refusal message, history-vs-ledger diffs (empty).

## 9. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| TBL-01 | The Tables view matches its API sources exactly across columns, filters, sorts, and per-table series; name divergence is disclosed via expansion; the full status progression including a linked, explained DONE/INCONCLUSIVE is observed |
| TBL-02 | Definition drift checks report seeded out-of-band DDL exactly (field, side, nature) with zero false positives on clean tables, and scheduled checks alert within one cycle |
| TBL-03 | Adopt-from-actual previews as a complete minimal plan, applies as one versioned event with verified ripple, refuses constraint-breaking adoptions with named reasons, and never exceeds its scope |
| TBL-04 | Table-scoped operations use the selection as their exact scope, delete is plan-governed, table-definition subsets round-trip, and all operations are UI/CLI equivalent |
| TBL-05 | The columns grid renders the published type-mapping table exactly per cell with settings provenance; physical renames are versioned edits and identity renames use a self-retiring, evented alias window with replication uninterrupted; column edits are plan-governed with constraint refusals; the history tabs equal the event ledger |
| TBL-06 | Column source and target physical names are independently editable against one identity: a rename on either side leaves the other untouched, replication continues uninterrupted, compare pairs by identity and prints both names, and colliding or reserved target names are refused with both names given |

## 10. Open Questions

**Contexts need an owning definition.** Named contexts are used by refresh (predicate variables), compare (recorded relaxation scope), and now this page's context preview — but no specification defines the concept itself: what a context is, what settings it may scope, how a context overlay interacts with the four-level provenance ladder, and who may enable one on which operations. Until that section exists (it belongs in the stream spec beside the settings ladder), every context reference in the set is a pointer to an undefined term — a documentation-completeness violation by our own standard, tracked here so it cannot be quietly forgotten. Beyond that: whether the drift check should run implicitly before every activation plan (making drift a plan input rather than a separate discovery) is attractive and probably right — it needs a cost measurement on wide streams first. The per-table change series' retention and granularity ride the metrics-store decisions in the statistics design (pending page). Bulk adopt (accept all drift across a stream in one plan) is an obvious request with an obvious risk; if offered, it takes the typed-confirmation treatment. SAP-specific table addition flows (HVR's separate SAP dialog) follow the SAP roadmap decision (sizing spec §12).
