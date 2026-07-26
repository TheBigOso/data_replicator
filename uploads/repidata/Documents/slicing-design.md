# Slicing — Design Specification

**Project:** Enterprise CDC Replication Platform (working name TBD)
**Document type:** Concept and design specification (feeds the master architecture document)
**Status:** Design complete — implementation phased (see Roadmap Phasing)
**Priority note:** Deliberately sequenced behind core refresh mechanics. This concept must be nailed down and proven before the advanced layers ship. Basic slicing and slice-level restartability are v1 because restartability cannot be retrofitted; the Advisor, AI layer, and slice map land in their own dedicated milestone.

---

## 1. Purpose and Positioning

Slicing divides a large source table into independent pieces so that refresh and compare operations can run in parallel, restart safely, and remain observable. It is the difference between a workable and an unworkable full reload when tables reach tens or hundreds of billions of rows.

HVR provides four slicing types but offers no guidance on which to use, no protection against the ways slicing can silently go wrong, and no visibility into a running sliced operation. Operators are left to discover — often at hour six of a production refresh — that they chose a strategy that multiplies source I/O, skews slice runtimes, or misassigns rows.

Our position: slicing is a first-class, guided, observable capability. The product recommends a strategy and explains why, refuses configurations known to be unsafe, shows exactly where a running operation stands, and lets a failure cost one slice instead of the entire run. Consistent with the platform's transparency principle, the product's own sharp edges are documented openly and, wherever possible, converted into guardrails the tool enforces rather than footnotes the user must remember.

## 2. The Core Problem: Why Strategy Choice Dominates

Consider a 100-billion-row Oracle table requiring a full historical reload. The naive serial `SELECT *` is a schedule-buster measured in days. Slicing is mandatory. But the *kind* of slicing determines whether parallelism helps or hurts:

The modulo trap. Modulo slicing (`mod(col, N) = k`) is HVR's easiest option and its most dangerous. A modulo predicate cannot use an index range scan, so on most databases each slice performs a full scan of the entire table, filtering out everything not in its remainder class. N slices can therefore mean N full scans of the same 100-billion-row table — the "easy" option multiplies total source I/O by the slice count. HVR never surfaces this. Our product does, both in documentation and directly in the UI when a user selects modulo on a large table.

Range-based strategies read only their piece. Boundary slicing on an indexed sorted key, partition-aligned slicing, and physical rowid-range slicing each touch only the rows in their own range. Total source I/O stays at roughly one table's worth regardless of slice count. For very large tables this is the difference between a 6-hour and a 60-hour operation.

Skew ruins balance. Equal key-ranges are not equal row-counts. A boundary plan cut naively across a skewed key produces one slice that runs 8x longer than the rest, and the whole operation waits on it. Balance must come from data statistics, not arithmetic on the key range.

## 3. Slicing Types

The platform supports all four HVR types for parity plus two types HVR lacks. Each type's mechanics, best-fit case, and hazards are documented publicly.

### 3.1 Boundary slicing (v1)

The user (or the Advisor) defines cut points on a column; each slice covers one range, from table minimum to the first boundary through the last boundary to table maximum. Boundaries may be numeric, string, or date values. Best fit: tables with an indexed, roughly-sorted key. Predicates are index-range-scannable, so each slice reads only its rows.

Improvement over HVR: boundaries can be auto-derived from optimizer histogram percentiles so slices are balanced by row count rather than by key arithmetic. Date boundaries evaluate through the platform's canonical type layer, fixing HVR's documented failure of boundary-on-dates in heterogeneous source/target pairs — a boundary instant means the same instant on Oracle and on Snowflake.

### 3.2 Partition-aligned slicing (v1 — no HVR equivalent)

When the source table is partitioned, slices align to partitions (or groups of partitions). The database prunes to exactly the relevant partition per slice; balance follows the partition scheme; no key math is needed. This is the default recommendation for any partitioned table and it is remarkable that HVR does not offer it as a named strategy.

### 3.3 Hash slicing — HVR "count slicing" (v1)

For columns where ranges are meaningless (strings, UUIDs), rows are assigned to slices by hashing: `mod(native_hash(col), N) = k`. HVR requires the user to hand-write this as a Restrict expression (e.g. `mod(coalesce(ora_hash(mycol),0),{hvr_slice_total})={hvr_slice_num}`). Our platform generates the expression automatically using each database's native hash function (`ora_hash`, `hashtext`, `checksum`, etc.). Hash slicing shares modulo's full-scan cost profile and carries the same UI warning.

### 3.4 Modulo slicing (v1, with guardrails)

Supported for parity: `mod(col, N) = k` on a numeric column. Ships with two protections HVR lacks. First, the full-scan cost warning appears in the UI at selection time on large tables, with a one-click switch to the Advisor's recommendation. Second, unsafe columns are refused outright: HVR documents that float columns and Oracle `NUMBER(*)` values with exponents beyond ±1E+37 can assign rows to the wrong slice in heterogeneous refreshes — silent data loss. Our column-safety check inspects type and value range from statistics and blocks such columns from modulo and hash slicing, stating why. A wrong-slice bug belongs in the tool's guardrails, not on page four of a limitations appendix.

### 3.5 Series slicing (v1)

One slice per distinct value (or explicit value list) of a low-cardinality column — country codes, company codes, regions. Improvement over HVR: the value list auto-populates from column statistics with per-value row counts displayed, so skew is visible before the user commits (a value holding 31% of rows is flagged, with the option to group small values and split large ones).

### 3.6 Physical rowid-range slicing (v1.x — no HVR equivalent)

For Oracle, slices are defined by physical rowid ranges derived from the table's extent map — the `DBMS_PARALLEL_EXECUTE` approach. Slices are balanced by data blocks, require no index, no key column, and no assumptions about data distribution, and each slice reads only its own blocks. For massive heap tables this is the strongest general answer available and the flagship differentiator of the slicing subsystem. PostgreSQL gains an equivalent via `ctid` ranges. Availability per source is documented in the capability matrix.

## 4. Strategy Selection Hierarchy

The default decision order, applied by the Advisor and documented publicly so users can follow the reasoning by hand:

1. Table is partitioned → partition-aligned slicing.
2. Oracle (or Postgres) heap table of significant size → rowid/ctid-range slicing.
3. Indexed sequential key (numeric or date) → boundary slicing with histogram-derived, row-balanced cut points.
4. Low-cardinality grouping column with acceptable skew → series slicing.
5. Otherwise → hash slicing, with the full-scan cost stated explicitly.
6. Modulo only on explicit user request, after the cost warning, on a verified-safe column.

## 5. The Slicing Advisor

The Advisor is a deterministic recommendation engine. It gathers what the source database already knows — no full table scans are ever required — and produces a ranked, explained, validated slicing plan.

### 5.1 Metadata collection

From optimizer statistics and catalog views only: row count and physical size; partition scheme and per-partition row counts; primary key and index columns with data types; column histograms and number-of-distinct-values; and, for Oracle, the extent map for rowid planning. Collection cost is a handful of catalog queries.

### 5.2 Skew detection

Histograms reveal hot values and lopsided distributions before any plan is committed. The Advisor reports skew concretely ("value CORP-001 holds 31% of rows; naive series slicing would make slice 3 run approximately 8x longer than the median") and compensates by cutting boundaries at row-count percentiles or grouping/splitting series values.

### 5.3 Plan validation via EXPLAIN

Before presenting a recommendation, the Advisor runs the database's EXPLAIN facility on the generated slice predicates and inspects the plans. If a slice predicate produces a full table scan where a range scan was expected, the Advisor says so and revises. The product checks its own work against the optimizer rather than assuming.

### 5.4 Column-safety guardrails

The Advisor enforces the refusals described in 3.4: float columns and out-of-range numeric values are blocked from modulo/hash slicing with an explanation; columns absent from the target are blocked for compare and row-wise refresh slicing (per the source/target rules in section 7); known-hazard patterns inherited from HVR's limitations list are encoded as checks, not documentation.

### 5.5 Known-schema knowledge base

HVR's documentation contains hand-written slicing hints for SAP cluster tables (slice RFBLG on BUKRS/BELNR/GJAHR, KOCLU on KNUMV, STXL on TDOBJECT, pool tables on TABNAME; never slice on MANDT). This is the right idea delivered in the wrong medium. The Advisor generalizes it: per-schema slicing recommendations are shippable advisor rules, so when SAP sources land on the roadmap, BSEG-grade guidance is built into the tool rather than buried in docs. The rule format is public, and customers can add rules for their own application schemas.

## 6. AI Explanation Layer

On top of the deterministic engine sits an optional AI layer. The engine computes; the AI explains and converses. Given the collected statistics, the candidate plans, and the EXPLAIN output, it produces plain-language reasoning — "your table is 2.4 TB across 96 monthly partitions with heavy skew toward the trailing six months; 48 partition-aligned slices with 12 parallel readers is recommended because..." — and answers what-if questions ("what if the DBA limits me to 4 sessions?" / "what does this do to source load during business hours?").

Deployment constraint: the AI layer must be optional and offline-tolerant. Air-gapped and classified environments cannot call a model API. The deterministic Advisor, including its structured explanations and skew reports, is fully useful standalone; the AI layer is an enhancement where connectivity and policy allow, never a dependency. Whether AI features are permitted is a per-hub policy setting.

## 7. Source/Target Slicing Rules (HVR parity)

For bulk refresh, slicing applies to the source table only. For compare and row-wise refresh, slicing may be defined on the source or the target, restricted to columns present on both sides. The platform enforces these rules in the UI at column-selection time rather than allowing a configuration that fails at runtime.

## 8. Parallel Writers (HVR parity)

Slicing parallelizes the source side; parallel writers parallelize the target side by splitting each slice's rows across multiple concurrent writer processes. The two combine freely. Parallel writers are supported on targets with a staging-file load path (Snowflake, Databricks, S3/ADLS, PostgreSQL via COPY), and are the recommended lever when the target, not the source, is the bottleneck. The Advisor's recommendation includes a parallel-writer count when target-side statistics suggest it.

## 9. Execution Semantics

### 9.1 Slice-level checkpoint and resume (v1 — cannot be retrofitted)

Every slice is an independent unit of work with its own durable state. A slice that completes is done forever; a slice that fails is individually retried (with backoff, honoring the pipeline's retry policy) without touching completed slices. A refresh that dies at hour seven costs one slice, not the run. This property shapes the file log layout for refresh data (per-slice file sequences) and therefore must exist from v1 even though the advanced slicing features come later.

### 9.2 Consistency

Where the source supports it, all slices of a refresh read as-of a single SCN/LSN so the reloaded table is transactionally coherent rather than a smear across the load window (inherits the consistent-snapshot design from the Scheduler and Refresh Modes specification). A slice retried after failure re-reads as-of the same point; if the source can no longer serve that point (e.g. ORA-01555 undo exhaustion), the failure is reported with the exact error and remediation guidance, and the operator chooses between retrying at a new coherent point or accepting per-slice points for append-style targets.

### 9.3 Interaction with stage-and-swap

Slice outputs land in the target staging area; the atomic swap to the live table occurs only when every slice has completed. A partially-complete sliced refresh is never visible to target readers.

## 10. Observability: the Slice Map

A running sliced operation is a map, not a spinner.

The slice map renders every slice as a tile colored by state (pending, running, done, failed), with summary metrics above it: slices completed, rows and bytes moved, live throughput, and an estimated finish time computed from completed-slice throughput rather than guesswork. The map answers, at a glance, the question that today goes unanswered for hours: where is my refresh and is it healthy?

### 10.1 Slice drill-in

Every tile is clickable. The drill-in shows the slice's exact range, the literal SQL predicate being executed against the source (full transparency about what the product is doing — no hidden queries), rows moved against the estimate, a throughput timeline, elapsed time, retry history, and the complete event log including verbatim source errors (e.g. ORA-01555 with timestamp). Pending slices display their planned range and predicate before execution, so an operator can sanity-check the entire plan at minute one instead of discovering a problem at hour six.

### 10.2 Data preview

The drill-in can display sample rows that actually came across for that slice — first and last rows received plus min/max key values — decoded on demand from the slice's staged change files on the hub or read back from the target staging table. This turns "is this slice pulling what I think it's pulling" from a guess into a glance, and for a failed slice the last-received rows are often the fastest diagnostic clue.

Access control: data preview is a privilege, not a default. The control plane ordinarily never exposes row contents. Preview requires the distinct data-viewer role; every preview action is written to the audit log (user, slice, timestamp); and a per-hub policy switch disables preview entirely for classified or regulated pipelines. The feature exists for the operator debugging at 2 AM without becoming a data-exposure surface a security package cannot approve.

### 10.3 API parity

The slice map, per-slice states, metrics, and event logs are all served by the public REST API (the UI is a pure client of it), so external monitoring — Datadog dashboards, custom tooling — sees exactly what the UI sees.

## 11. HVR Parity and Differentiation Matrix

| Capability | HVR 6 | This platform |
|---|---|---|
| Modulo slicing | Yes | Yes, with UI cost warning and unsafe-column refusal |
| Count/hash slicing | Yes, hand-written Restrict expression | Yes, expression auto-generated per DBMS |
| Boundary slicing | Yes, manual boundaries | Yes, plus histogram-derived row-balanced boundaries |
| Series slicing | Yes, manual value list | Yes, plus auto-populated values with per-value row counts and skew flags |
| Partition-aligned slicing | No | Yes (v1) |
| Physical rowid/ctid-range slicing | No | Yes (v1.x) |
| Strategy recommendation | None | Slicing Advisor with EXPLAIN validation |
| AI-assisted explanation | None | Optional, offline-tolerant layer |
| Float / big-NUMBER wrong-slice hazard | Documented limitation | Blocked by column-safety guardrail |
| Boundary-on-dates, heterogeneous | Documented as not working | Fixed via canonical type layer |
| Slice-level restart | Whole-job oriented | Per-slice checkpoint, retry, and resume (v1) |
| Progress visibility | Job log text | Slice map, drill-in, data preview, ETA |
| Source-only slicing for bulk refresh; shared-column rule for compare/row-wise | Yes | Yes, enforced at configuration time |
| Parallel writers | Yes (staging targets) | Yes (staging targets), Advisor-recommended counts |
| SAP cluster-table slicing hints | Documentation prose | Advisor knowledge-base rules (ships with SAP sources) |

## 12. Roadmap Phasing

| Phase | Scope |
|---|---|
| v1 | Boundary, partition-aligned, hash, modulo (with warnings and guardrails), series slicing; source/target rules enforced in UI; parallel writers; slice-level checkpoint/resume; consistent-snapshot semantics; stage-and-swap integration |
| v1.x | Rowid-range slicing (Oracle), ctid-range (PostgreSQL); column-safety checks extended per source |
| Milestone 2 — "nail it down" | Slicing Advisor (stats collection, skew detection, EXPLAIN validation, knowledge-base rules); optional AI explanation layer; slice map UI with drill-in, data preview (RBAC + audit + policy switch), and API parity |

## 13. Test Plan

Phased plan; the standing rule applies (procedure executed, results observed, evidence archived — no procedure, no pass), and the full suite reruns as regression on every merge touching this area.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | v1 slicing mechanics | SLC-01 through SLC-10, SLC-17 | Skew corpus + chaos harness | v1 slicing and per-slice checkpointing implemented | Union invariant, guardrails, failure recovery, and parallel writers proven |
| B | Physical-range slicing (v1.x) | SLC-16 | Indexless heap fixture | Rowid/ctid slicing implemented | Block balance within tolerance, no index required |
| C | Advisor and slice map (milestone 2) | SLC-11, SLC-12, SLC-13, SLC-14, SLC-15 | Trap fixtures, offline namespace, Playwright | Advisor and map implemented | EXPLAIN trap caught; offline completeness; RBAC matrix and parity proven |

### 13.1 Methods

Slicing correctness reduces to one invariant tested everywhere: **the union of slices equals the table exactly — no row missing, no row twice** — proven by the compare feature after every sliced operation in every test below.

**The skew corpus.** The TPC-C lab schema is augmented with deliberately hostile fixtures: injected value skew (one customer holding 31% of order lines), float and out-of-range NUMBER columns for guardrail refusal tests (SLC-05), and partitioned variants for pruning verification (SLC-03). Balance criteria (SLC-02, SLC-16) are measured, not eyeballed — per-slice row and block counts asserted within tolerance.

**Advisor tests** seed traps and assert they're caught: a fixture whose obvious key produces full-scan slice predicates must be detected by EXPLAIN validation and the plan revised (SLC-14); every advisor run in CI executes with the AI layer disabled and no network to prove offline completeness (SLC-15).

**Failure tests** kill slice workers and the hub mid-refresh at randomized points (SLC-07, SLC-08) and include a permanently-failing slice to prove the swap never fires on a partial set while readers poll the live table throughout (SLC-09). Snapshot coherence runs under concurrent update load (SLC-10).

**Observability and access tests**: ETA accuracy is measured against benchmark runs (SLC-11); drill-in predicate display is asserted against the actually-executed SQL captured from the source session (SLC-12); the data-preview RBAC matrix — no role, role granted, hub policy disabled — is exercised with audit-log assertions on every path (SLC-13).

## 14. Test Procedures

All procedures end with the union invariant unless stated: compare proves the union of slices equals the source exactly. Fixtures come from the skew corpus (section 13).

### SLC-01 — Boundary slicing correctness and plan quality
**Steps:** (1) Boundary-slice the indexed-key fixture into 8 slices. (2) Capture EXPLAIN for each slice predicate. (3) Run; compare. (4) Cross-check per-slice row IDs for overlap.
**Expected:** All 8 plans show index range scans; compare clean; zero overlapping rows across slices.
**Evidence:** 8 plans, compare report, overlap query result (0).

### SLC-02 — Histogram-balanced boundaries under skew
**Steps:** (1) On the injected-skew fixture, generate histogram-derived boundaries for 10 slices. (2) Run; record per-slice row counts.
**Expected:** Every slice within ±15% of the mean row count despite the skewed key.
**Evidence:** Per-slice count table with deviation column.

### SLC-03 — Partition-aligned pruning
**Steps:** (1) Partition-slice the partitioned fixture. (2) Run with source execution statistics enabled. (3) Map each slice's partitions-accessed against its assignment.
**Expected:** Each slice touches exactly its assigned partitions; zero cross-partition reads.
**Evidence:** Execution-statistics mapping table.

### SLC-04 — Modulo full-scan warning
**Steps:** (1) In the UI, select modulo slicing on the large fixture. (2) Capture the warning and the one-click advisor alternative. (3) Proceed anyway; check the acknowledgment in the event log. (4) Repeat via REST API.
**Expected:** Warning surfaced in both UI and API paths; acknowledgment logged with user identity.
**Evidence:** Screenshot/API response, event log entry.

### SLC-05 — Unsafe-column refusal
**Steps:** Attempt modulo and hash slicing on (a) the float-column fixture, (b) the out-of-range NUMBER fixture, via UI and API.
**Expected:** All four attempts refused with the documented explanation naming the hazard; no job created.
**Evidence:** Refusal messages, job table unchanged.

### SLC-06 — Heterogeneous date boundaries
**Steps:** (1) Date-boundary slice Oracle→Snowflake on the datetime fixture spanning timezone-sensitive values. (2) Run; compare. (3) Spot-audit boundary-adjacent rows on both sides.
**Expected:** Compare clean; every boundary-adjacent row in the correct slice on both platforms.
**Evidence:** Compare report, boundary audit sample.

### SLC-07 — Slice worker kill
**Steps:** (1) Start a 16-slice refresh. (2) Kill one slice's worker process at a randomized point (repeat run 5×). (3) Observe retry; complete; compare.
**Expected:** Only the killed slice retries (others' checkpoints untouched); all 5 runs compare clean.
**Evidence:** Retry logs, 5 compare reports.

### SLC-08 — Hub kill mid-refresh
**Steps:** (1) Start a sliced refresh. (2) Kill the hub at ~50%. (3) Restart; observe resume. (4) Compare; duplicate-check on the target (key count vs distinct).
**Expected:** Resume from per-slice checkpoints; compare clean; zero duplicate keys.
**Evidence:** Resume log, compare + duplicate query results.

### SLC-09 — No partial swap
**Steps:** (1) Configure one slice to fail permanently (poison fixture row). (2) Run the refresh with a reader polling live tables throughout. (3) After the failure verdict, inspect live tables.
**Expected:** Swap never fires; readers observed only the prior complete data at every poll; staging cleaned per policy.
**Evidence:** Reader log, live-table state, swap event absence.

### SLC-10 — Snapshot coherence across slices
**Steps:** (1) TPC-C at full rate. (2) Snapshot-consistent 16-slice refresh. (3) Verify every row's ORA_ROWSCN-equivalent ≤ the run's snapshot point; FK coherence audit across sliced tables.
**Expected:** Zero post-snapshot rows in any slice; zero FK orphans.
**Evidence:** SCN boundary check, FK audit.

### SLC-11 — Slice map API/UI parity and ETA accuracy
**Steps:** (1) During a benchmark refresh, sample slice states via REST and via UI DOM (Playwright) at 10s intervals. (2) Record ETA at each sample; compute error vs actual finish over the run's second half.
**Expected:** REST and UI agree at every sample; second-half ETA error under 20%.
**Evidence:** Parity sample log, ETA error series.

### SLC-12 — Predicate transparency
**Steps:** (1) During a run, capture actually-executed SQL from the source session for 4 slices. (2) Diff against the drill-in's displayed predicates. (3) Before the run, capture planned predicates for pending slices; verify they match what later executes.
**Expected:** Byte-equivalent predicates displayed vs executed; pending previews match execution.
**Evidence:** Session capture vs drill-in diffs.

### SLC-13 — Data preview RBAC matrix
**Steps:** Three passes: (a) user without data-viewer requests preview; (b) user with the role requests preview; (c) hub preview policy disabled, privileged user requests preview. Check the audit log after each.
**Expected:** (a) denied, denial audited; (b) served, access audited with user/slice/time; (c) unavailable to all roles, attempt audited.
**Evidence:** Three response captures, three audit entries.

### SLC-14 — Advisor EXPLAIN validation catches the trap
**Steps:** (1) Run the Advisor on the trap fixture (obvious key whose predicates full-scan). (2) Inspect the Advisor's validation output and revised plan. (3) Execute the revised plan; capture EXPLAIN.
**Expected:** Trap detected and stated; revised plan's predicates range-scan or prune; run compares clean.
**Evidence:** Advisor output, revised-plan EXPLAINs.

### SLC-15 — Advisor offline completeness
**Steps:** (1) Disable the AI layer; remove external network from the hub (namespace). (2) Run the Advisor across the full fixture corpus. (3) Verify recommendation + structured explanation + skew report present for each.
**Expected:** Functionally complete output for every fixture; zero outbound connection attempts (network capture).
**Evidence:** Advisor outputs, empty egress capture.

### SLC-16 — Rowid-range balance without index
**Steps:** (1) Drop all indexes on the 10M+ row heap fixture. (2) Rowid-range slice into 12; run. (3) Record per-slice block counts.
**Expected:** Slices within ±10% by blocks; run succeeds with no index present; compare clean.
**Evidence:** Block-count table, compare report.

### SLC-17 — Parallel writers throughput and correctness
**Steps:** (1) Benchmark a fixed sliced refresh into the staging target with 1 writer; record load time. (2) Repeat with the Advisor-recommended writer count. (3) Compare both runs' targets against source.
**Expected:** Measurable throughput gain (recorded, becomes the published number); both compares clean.
**Evidence:** Timing pair, compare reports.

## 15. Acceptance Criteria (traceability matrix rows)

Every item below must have passing tests before its feature is considered done. These rows join the master feature-to-test traceability matrix.

| ID | Criterion |
|---|---|
| SLC-01 | Boundary slicing on an indexed numeric key: EXPLAIN shows index range scan per slice; union of slices equals full table exactly (compare-verified); no row appears in two slices |
| SLC-02 | Histogram-derived boundaries on a skewed key produce slices within ±15% row-count of each other on the TPC-C corpus with injected skew |
| SLC-03 | Partition-aligned slicing prunes to exactly the expected partitions (verified via source execution statistics) |
| SLC-04 | Modulo selection on a table above the size threshold surfaces the full-scan warning; proceeding logs the acknowledgment |
| SLC-05 | Modulo/hash on a float column or out-of-range NUMBER is refused with the documented explanation |
| SLC-06 | Date boundary slicing Oracle → Snowflake assigns every row to the correct slice across the type boundary (compare-verified) |
| SLC-07 | Kill a slice worker mid-transfer: only that slice retries; completed slices are untouched; final compare shows source equals target |
| SLC-08 | Kill the hub mid-refresh: on recovery, the operation resumes from per-slice checkpoints with zero duplicate rows at the target |
| SLC-09 | Sliced refresh with one deliberately failing slice never swaps a partial table into the live target; readers see the old data throughout |
| SLC-10 | All slices of a snapshot-consistent refresh read as-of one SCN (verified against a source workload running concurrent updates) |
| SLC-11 | Slice map states, metrics, and ETA are served identically via REST API and UI; ETA error under 20% in the second half of a benchmark run |
| SLC-12 | Drill-in displays the literal executed predicate; pending slices show planned predicates before execution |
| SLC-13 | Data preview without the data-viewer role is denied; with the role, the access is present in the audit log; with the hub policy disabled, preview is unavailable to all roles |
| SLC-14 | Advisor recommendation on the lab corpus: EXPLAIN validation catches a seeded full-scan predicate and revises the plan |
| SLC-15 | Advisor operates fully (recommendation + structured explanation) with the AI layer disabled and no external connectivity |
| SLC-16 | Rowid-range slicing on a 10M+ row lab table balances slices within ±10% by blocks and requires no index |
| SLC-17 | Parallel writers on a staging target increase load throughput measurably versus single writer on the benchmark corpus, with correctness compare-verified |

## 16. Open Questions

Slice-count and reader-count defaults need empirical tuning against the benchmark corpus before recommendations harden. The interaction between rowid-range slicing and tables undergoing heavy concurrent DML (row movement across extents) needs a documented consistency statement. Whether ctid-range slicing is safe under PostgreSQL autovacuum timing is a research item before v1.x. The exact skew threshold at which the Advisor switches from series to hash slicing is TBD from lab data.
