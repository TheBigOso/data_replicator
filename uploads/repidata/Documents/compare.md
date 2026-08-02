# Compare — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design; the platform's trust mechanism

---

## 1. Purpose and Positioning

Compare answers the only question that ultimately matters: **is the target equal to the source?** Everything else the platform does is machinery; compare is proof. It is also load-bearing twice over: customers use it for audit and drift detection (Mode 3 streams alert on divergence nightly), and *we* use it — every CI run in every test plan in this document set ends with a compare gating the merge. The product proves itself with the same instrument it sells, which is the strongest statement of confidence a replication vendor can make, and the reason this specification tolerates zero ambiguity.

A compare that lies is worse than no compare at all. Both failure directions are specified against: **false negatives** (differences missed — the audit criteria) and **false positives** (differences invented — the canonicalization and online criteria), because a compare that cries wolf under normal replication latency trains operators to ignore it.

## 2. The Two Compare Methods

### 2.1 Bulk compare — cheap answer to "are we equal?"

Bulk compare computes checksums over row data — per table, and per block of rows within a table — on both sides and compares the digests. Cost approaches a single scan on each side with minimal network (checksums travel, not rows). The answer is binary per block: equal, or not. When blocks differ, bulk compare has localized *where* to look, which is exactly what row-wise compare consumes. Below even bulk sits **row-counts-only** — count both sides, compare nothing else — the cheapest sanity tier and the first number in every sync report. The tiers compose: counts, checksums, row-wise on the differing blocks.

### 2.2 Row-wise compare — the exact difference set

Row-wise compare walks both sides key-ordered and produces the precise difference inventory, classified per row: **missing on target**, **extra on target**, **different** (same key, different values — with the differing columns identified). The output is the difference report (section 5) and, optionally, the input to row-wise refresh: the repair path is literally "apply this report" (refresh spec REF-05/06). The two methods compose: bulk to find the smoke cheaply, row-wise on the differing blocks to find the fire — the composed mode is the default for large tables.

### 2.3 Structure before data — do we have all the columns?

Compare verifies **structure first, data second**, per table: the table exists on both sides; the column set matches the stream's identity mapping (every expected column present, no unexplained extras unless the keep-existing-structure policy declared them); types are compatible per the published type-mapping table; and key/uniqueness expectations hold. A structural mismatch **short-circuits the data compare for that table** with a distinct verdict — comparing rows across mismatched columns produces garbage diffs, and the report should say "column TIER missing on target" rather than flagging ten million rows as different. Structure results are a first-class section of every report.

### 2.4 One source, many targets

A single compare run can verify one source against multiple targets: the source side is read once (its rows or checksums computed once) and evaluated against each target — the broadcast-topology audit case, at the cost of one source scan. The report carries a per-target section; each target gets its own verdict.

## 3. Canonicalization — comparing across heterogeneous systems honestly

Comparing Oracle to Snowflake means comparing values that are stored, typed, and encoded differently, and every false positive lives in that gap. The platform canonicalizes both sides to a defined comparison form before hashing or diffing, per the **published canonicalization table**: numeric scale and trailing-zero rules, timestamp normalization to UTC with per-type precision rules (a source `DATE` compared at the precision both sides can represent), character comparison in a defined normalization form and collation, trailing-space semantics per type family, NULL vs empty-string per the documented per-class rule. Where a target genuinely cannot represent a source value exactly (documented lossy mappings), compare applies the mapping's declared tolerance rather than flagging every affected row — and the report notes which rules were active.

Operator-controlled relaxations are per-compare settings: **column exclusions** (skip volatile columns — ETL timestamps, computed audit fields), **tolerances** (float epsilon; timestamp jitter windows), and **difference class filters** (ignore missing-on-target, extra-on-target, or changed rows — the mirror of the refresh repair filters, REF-10, for compares where one class is intentional) — all recorded in the report, because a compare's verdict is meaningless without knowing what it was allowed to ignore.

One consequence of canonicalization deserves emphasis because HVR behaves otherwise: **verdicts are direction-independent.** HVR performs the comparison at the "write" location with that location's type sensitivity — its own documentation walks through an Ingres/Oracle empty-string-versus-NULL case where comparing A→B reports the tables identical while B→A reports them different. A verdict that depends on which side you called the source is not a verdict. Here both sides canonicalize to the same comparison form under the same published rule before anything is compared, so swapping read and write sides cannot change the answer — CMP-06 asserts it by running its corpus in both directions.

## 4. Online Compare — truth under live replication

Comparing while replication runs is the normal case, and naive comparison lies: a change captured but not yet applied shows as a difference that is really just latency in flight. The online algorithm:

1. Compare both sides; collect candidate differences.
2. For each candidate, check the in-flight window: the region between the source position when the compare read the source and the target's applied position (from the state table — the platform knows exactly what the target has seen).
3. Candidates attributable to in-flight changes are **re-checked after the stream's applied position passes the compare's source position**; only differences that persist are reported.

The report separates **confirmed differences** from **transient candidates resolved during the run** (count shown — a healthy busy system resolves many), so the operator sees both the verdict and the evidence that the verdict accounted for motion. A compare on a paused or quiet stream skips the machinery and says so.

One operational note where HVR documents a hazard: HVR's equivalent mode accumulates transaction files for as long as an online compare job sits suspended — unbounded disk growth with no ceiling but the volume. Here the in-flight window rides the ordinary file-log acknowledgment and GC discipline under the file-store quota machinery (ARC-13): a suspended compare is a visible capacity line-item with an alert, never a silent disk filler.

### 4.1 Online without capture — the double compare

Mode 2 streams have no capture running, and the in-flight algorithm needs one — so HVR's alternative is kept, because it is the right answer: **compare twice and report only the differences that occur both times.** Two variants: a fixed **delay** between passes, or — where a stream exists — a **cycle flush**, waiting for a complete capture-and-integrate cycle between passes so in-flight changes have landed. The honesty requirement is stated with the mode: the intersection is a *persistent-difference filter, not a proof* — a row changing between passes can evade detection or appear once — and the report labels double-compare verdicts as such, with both pass timestamps. Where the source supports consistent reads, a pass can additionally pin its source read **as-of a position** (now, a timestamp, a transaction sequence, or an SCN — the refresh snapshot machinery reused), with the as-of recorded in the report, because "identical as of *when*?" is the auditor's question.

## 5. The Difference Report and Repair

The report is a first-class, archivable artifact: per table — row counts both sides, difference counts by class (missing/extra/different), the active canonicalization rules, exclusions, and tolerances; per difference (row-wise) — the key, the classification, and for value differences the differing columns with both canonical values (subject to the same RBAC and audit as slice data preview — SLC-13's regime applies verbatim). From the report: **repair** generates the row-wise fix set (into a target-write job with the refresh engine), or exports for external review. Every scheduled compare's report is retained per the retention policy; drift alerts (SCH-09) link to the exact report that fired them.

## 6. The Sync Report — daily proof of health

The gap in every replication product, HVR included: all the verification machinery exists, but nobody closes the loop into something a data owner actually reads. The **sync report** is that closure — one artifact per stream answering the three questions that matter:

**Do we have all the rows?** Row counts per table, source and target, with missing/extra counts from compare.
**Do we have all the columns?** The structure verification of 2.3, per table: columns present, types compatible, keys intact.
**Does the data match?** The match rate — matched rows over compared rows — with differences classified (missing / extra / different) and the online algorithm's transient accounting shown, so a busy healthy system reads as healthy.

### 6.1 When it's produced

Two triggers, one format: **on schedule** — daily by default per stream (any cadence the scheduler supports; rides Mode 3's scheduled compare), and **on demand** — every manually invoked compare emits the same report. One format everywhere means the 2 AM ad-hoc compare and the boardroom daily are the same document, and trends line up across both.

### 6.2 What's in it

Header: stream, period covered, source and target positions as-of the run (the auditor's "as of when?"). Structure section per table (2.3 results). Data section per table: source rows, target rows, matched, missing, extra, different, match rate, transient-resolved count. Replication activity for the period: changes captured and applied, refresh runs completed, latency percentiles. A one-line **verdict** per stream — IN SYNC, DRIFT DETECTED (with the affected tables), or STRUCTURE MISMATCH — and a trend strip against the last N reports so a slow degradation is visible before it's an incident. The daily run uses the cheapest sufficient method by default (bulk checksums plus counts); on any block difference it escalates to row-wise on the affected blocks automatically (configurable), so the daily answer is exact, not just "something differs."

### 6.3 Delivery and retention

Delivery is per stream, multi-sink: the Reports tab in the UI, email, webhook, and **file drop to a directory** — the air-gap answer, where a mail relay may not exist but a watched folder always does. All sinks receive the same content (rendered per medium); every report is archived under the retention policy; drift verdicts raise the standard drift alert (SCH-09) linking the exact report. The report is also available via REST like everything else, so a customer's own portal can embed it.

## 7. Direct File Compare

Comparing a file target (S3, ADLS, local directories) has a classic failure mode: routing the comparison through an external-table layer (Hive and kin) lets the deserializer coerce types, and the compare inherits the coercion's lies. **Direct file compare** reads and parses the files itself: the files of each table are sliced and distributed to **prereader subtasks** (count configurable per table), each of which reads, sorts, and parses its files into compressed, encrypted intermediate files (the intermediate directory is a per-location setting); the intermediates are then compared against the database side through the normal engine — canonicalization, difference classification, and reporting all identical. HVR parity on the mechanics, with its stated gaps as our roadmap: HVR's direct file compare excludes Avro, Parquet, and JSON; native columnar parsing (Arrow-based) for Parquet first is planned as a v1.x differentiator, since Parquet *is* the lake format. Structural limits are honest and documented: blob-style file streams (no table structure — files as byte sequences) cannot be compared this way, and XML requires one table per file.

## 8. Scope, Slicing, Scheduling

Compare scope mirrors refresh scope: stream, table subset, per-table predicates (compare only March; compare only rows touched by the incident). Large tables slice for compare exactly as for refresh — same strategies, same checkpoint-resume, same map (the union invariant means a sliced compare's verdict equals an unsliced one's, and SLC procedures already prove union correctness). Scheduling: ad-hoc, or recurring as Mode 3's scheduled compare with drift alerting — all under the scheduler's calendars and policies.

## 9. HVR Parity Matrix

| HVR compare concept | This platform | Delta |
|---|---|---|
| hvrcompare bulk (checksum) | Bulk compare, per-table and per-block digests | Kept; block localization feeds row-wise |
| hvrcompare row-wise | Row-wise with classified difference inventory | Kept |
| Online compare (live replication) | In-flight window + re-check algorithm, transient counts reported | Kept; the motion accounting is shown |
| Repair from compare | Repair via the row-wise refresh engine | One engine (see Refresh) |
| Slicing | Full slicing spec applies | Kept, deepened |
| Filters/context variables | Per-table predicates, column exclusions, tolerances | Structured settings, recorded in the report |
| Heterogeneous type handling | Published canonicalization table with per-class rules | Documented, not folklore |
| Compare events/results | Archivable reports, drift alerts linked to reports | Audit-grade retention |
| Compares table structures and data | Structure-first compare with short-circuit and named discrepancies | Kept, made a verdict class |
| One source vs multiple targets | Single-read multi-target compare with per-target verdicts | Kept |
| Direct file compare (prereaders, intermediate dir) | Same mechanics: sliced prereaders, compressed/encrypted intermediates | Kept |
| Direct file compare excludes Avro/Parquet/JSON | Native Parquet (Arrow) planned v1.x | Their gap, our roadmap |
| No integrated periodic sync report | Daily sync report: rows, columns, match rate, verdict, trend — scheduled and on-demand, one format | New — the closed loop |
| Comparison performed at the write location with its type sensitivity; direction can change the verdict | Both sides canonicalized under published rules; verdicts direction-independent | The Ingres/Oracle ambiguity designed out |
| Table Row Counts Only | Row-counts-only tier beneath bulk; the sync report's first number | Kept |
| Only Count Certain Differences (-m) | Difference class filters, recorded in the report | Kept; relaxations always named |
| Online modes: combine-with-captured / compare-twice-with-wait / flush-cycle | In-flight re-check where capture runs; double compare (delay or cycle-flush) where it doesn't, labeled a heuristic with pass timestamps | Kept; honesty labels added |
| Suspended online compare accumulates tx files (unbounded disk) | In-flight window under file-log GC and quota machinery (ARC-13); alerted, bounded | Hazard capped structurally |
| Flashback select-moment for compare (Now / time / tx_seq / SCN) | As-of-position source pinning via the refresh snapshot machinery, recorded in the report | Kept; "as of when?" always answered |
| Keep Difference Files (binary diff + viewer) | First-class archivable difference report with RBAC'd inspection | Kept, upgraded |
| Parallel sessions; prereaders per table | Table parallelism and prereaders per the slicing and direct-file-compare designs | Kept |
| Scheduling incl. delay-suspended; entry points; Repeat Compare from event | Scheduler-native; scoped-surface pre-fill and idempotent repeat (stream 6.7) | Same pattern everywhere |

## 10. Test Plan

Phased; standing rule applies. The suite is self-referential by design — compare verifies the platform, so compare itself is verified against **externally computed ground truth** (independent SQL differencing scripts, not the product's own code) in every correctness procedure. Full CMP suite reruns on merges touching compare, canonicalization, or state-position code.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Correctness vs ground truth | CMP-01, CMP-02, CMP-05 | Lab, external differ as oracle | Both methods implemented | Zero false negatives and zero false positives on the seeded corpus |
| B | Heterogeneous honesty | CMP-06, CMP-07 | Oracle→Postgres/Snowflake-class lab pair | Canonicalization table implemented | Type-gap corpus clean; relaxations honored and recorded |
| C | Online truth | CMP-03, CMP-15 | Lab under full TPC-C + Mode 2 fixture | Phase A exit; state-position integration | No false positives under load; transients accounted; double compare and pinning proven |
| D | Repair and reporting | CMP-04, CMP-08 | Lab + scheduler | Refresh row-wise available | Repair round-trip and report/alert integration proven |
| E | Sync report and file compare | CMP-09, CMP-10, CMP-11, CMP-12, CMP-13, CMP-14 | Lab + delivery sinks + file-location fixtures | Phases A–D exits | Report accuracy, all sinks, structure verdicts, and direct file compare proven |

### 10.1 Methods

Ground truth is the discipline: every seeded-difference corpus is independently diffed by plain SQL scripts maintained outside the product, and compare's output must match the oracle's exactly — the product never grades its own homework in its own trial. The seeded corpus covers every difference class, keys at type extremes, and rows engineered to hash-collide at the block level (bulk must still localize correctly). The heterogeneous corpus is built from the documented type-mapping table: one fixture per mapping rule, including every documented lossy mapping. Online tests measure the property that matters — zero confirmed false positives across sustained full-rate replication — and chaos variants kill the compare job mid-run to verify checkpoint resume produces the identical report.

## 11. Test Procedures

### CMP-01 — Zero false positives on identical data
**Steps:** (1) Refresh a 20-table stream to a verified-identical state (external differ confirms). (2) Run bulk, row-wise, and composed compares. (3) Any reported difference is a failure — investigate, don't rationalize.
**Expected:** Zero differences from all three methods; reports show active rules.
**Evidence:** Three reports, external differ confirmation.

### CMP-02 — Seeded differences detected exactly
**Steps:** (1) Seed the corpus: 500 missing, 500 extra, 500 changed rows (single- and multi-column changes, key-extreme values, block-collision rows) across 10 tables. (2) Run composed compare. (3) Diff compare's inventory against the external oracle's, row by row and classification by classification.
**Expected:** Exact match — every seeded difference found, correctly classified, differing columns correctly identified; nothing unseeded reported.
**Evidence:** Inventory-vs-oracle diff (empty), corpus manifest.

### CMP-03 — Online compare under full load
**Steps:** (1) TPC-C at full rate through a healthy stream. (2) Run online compares continuously for one hour. (3) Assert zero confirmed differences; record transient-resolved counts. (4) Inject one real difference (manual target mutation) mid-run; assert it is confirmed, not dissolved as transient.
**Expected:** Zero false positives across the hour; the injected real difference is caught and confirmed; transient accounting present in every report.
**Evidence:** Hourly report set, injection case report.

### CMP-04 — Repair round-trip
**Steps:** (1) From CMP-02's confirmed report, invoke repair. (2) Verify the generated fix set matches the difference inventory; apply. (3) Re-compare (all methods); external differ confirms.
**Expected:** Re-compare clean; fix set row-for-row matched the inventory; writes O(differences) per REF-05's property.
**Evidence:** Fix-set audit, clean re-compare reports, oracle confirmation.

### CMP-05 — Bulk/row-wise/composed agreement
**Steps:** (1) On the seeded corpus, run all three methods independently. (2) Bulk must flag exactly the blocks containing seeded differences; row-wise and composed must produce identical inventories.
**Expected:** Block localization exact (including the hash-collision fixtures); method agreement total.
**Evidence:** Cross-method comparison matrix.

### CMP-06 — Heterogeneous canonicalization corpus
**Preconditions:** Oracle-class → Snowflake-class pair loaded with the type-gap corpus (timestamp precisions, numeric scale/trailing zeros, character normalization cases, NULL/empty-string, documented lossy mappings).
**Steps:** (1) Replicate the corpus; verify externally that the data is semantically equal per the mapping table. (2) Compare. (3) Then mutate one value per type family and re-compare. (4) Rerun steps 2 and 3 with the read and write sides swapped.
**Expected:** Step 2 zero differences (no false positives from type gaps); step 3 exactly the mutated rows flagged (canonicalization doesn't mask real differences); lossy-mapping rows handled per their declared tolerance and noted in the report; step 4 verdicts identical to steps 2–3 in every case — direction never changes the answer.
**Evidence:** Both reports, corpus manifest with per-rule cases.

### CMP-07 — Exclusions and tolerances honored and recorded
**Steps:** (1) Add a volatile ETL-timestamp column and a float column with epsilon-scale noise to a fixture. (2) Compare without relaxations (differences expected), then with the column excluded and epsilon tolerance set. (3) Inspect reports.
**Expected:** Relaxed run clean; both reports enumerate exactly the active exclusions/tolerances; an unrelated seeded difference is still caught in the relaxed run.
**Evidence:** Paired reports.

### CMP-08 — Scheduled compare, drift alert, report retention
**Steps:** (1) Mode 3 stream, nightly compare on the virtual clock. (2) Seed drift; advance to the next cycle. (3) Follow the drift alert to its linked report; verify the report archive across simulated weeks against the retention policy. (4) Kill a compare job mid-run (chaos variant); resume; verify the final report equals an uninterrupted run's.
**Expected:** Alert within one cycle linking the exact report (SCH-09 alignment); retention policy enforced; checkpoint-resumed report identical to uninterrupted.
**Evidence:** Alert-report linkage, archive audit, resumed-vs-uninterrupted report diff (empty).

### CMP-09 — Sync report content accuracy
**Preconditions:** Three lab streams engineered to three states: fully in sync; seeded data drift (known counts per class); seeded structure mismatch (one column dropped on one target table).
**Steps:** (1) Run the scheduled daily report (virtual clock) across all three. (2) Audit every number in each report against externally computed ground truth: row counts, missing/extra/different counts, match rates, activity stats, and the verdict line. (3) Verify the drift report escalated to row-wise on exactly the differing blocks.
**Expected:** Every figure matches ground truth; verdicts are IN SYNC / DRIFT DETECTED / STRUCTURE MISMATCH respectively; the structure-mismatch table's data compare short-circuited with the column named.
**Evidence:** Three reports vs oracle computations, escalation log.

### CMP-10 — Delivery sinks, including air-gap
**Steps:** (1) Configure one stream's report to all four sinks: UI, email (lab SMTP), webhook (capture endpoint), file drop. (2) Trigger the daily run. (3) Verify all four deliveries carry identical content; for the file-drop path, run with hub egress blocked (namespace) and verify delivery still succeeds with zero external connection attempts. (4) Verify archive and retention behavior over simulated weeks.
**Expected:** Four identical deliveries; file drop fully functional air-gapped; archive obeys retention.
**Evidence:** Delivery captures, egress capture (empty), archive audit.

### CMP-11 — On-demand report parity
**Steps:** (1) Run a manual compare via UI and via CLI on the drifted stream. (2) Diff both outputs against the scheduled report format and against each other. (3) Verify both appear in the report archive alongside scheduled ones.
**Expected:** One format everywhere; manual reports archived identically; UI and CLI outputs equivalent (parity rule).
**Evidence:** Format diffs (empty), archive listing.

### CMP-12 — Structure verdicts
**Preconditions:** Fixtures: column missing on target; type drifted beyond mapping compatibility; extra target column under keep-existing-structure (declared); extra undeclared column.
**Steps:** (1) Compare each fixture. (2) Inspect structure sections and verdicts.
**Expected:** Missing and drifted-type fixtures short-circuit data compare with the discrepancy named; declared extra column passes with a note; undeclared extra is flagged; no garbage row diffs anywhere.
**Evidence:** Four report structure sections.

### CMP-13 — Direct file compare
**Preconditions:** File-location fixture (CSV on lab object store) populated by a TimeKey stream; seeded differences on the database side.
**Steps:** (1) Run direct file compare with 4 prereaders per table; verify slicing across prereaders and intermediate files in the configured directory (compressed, encrypted — spot-check unreadability). (2) Verify the difference inventory against the external oracle. (3) Verify intermediates are cleaned per policy post-run. (4) Attempt compare on a blob-style stream; verify the documented refusal.
**Expected:** Inventory exact; intermediates encrypted and cleaned; prereader distribution observed; blob refusal matches documentation.
**Evidence:** Oracle diff (empty), directory audits, refusal message.

### CMP-14 — Multi-target compare
**Preconditions:** Broadcast stream, one source, two targets; drift seeded on target B only.
**Steps:** (1) Run one compare of source vs both targets. (2) Verify the source was read once (session/scan audit). (3) Inspect per-target sections and verdicts.
**Expected:** Target A clean, target B's seeded drift exactly reported; single source read; verdicts independent.
**Evidence:** Scan audit, per-target report sections vs seed list.

### CMP-15 — Counts-only, class filters, and the double compare
**Preconditions:** In-sync and drifted lab streams; soft-delete-style fixture; a Mode 2 stream (no capture) with a scripted live-change driver; external oracle scripts.
**Steps:** (1) Run row-counts-only on both streams; assert counts exact against the oracle and runtime measurably below bulk's. (2) Row-wise compare with the no-deletes class filter on the soft-delete fixture: the filtered class is absent from results and diff output, the report names the active filter, and an unfiltered rerun surfaces it. (3) On the Mode 2 stream under live changes, run the double compare with a fixed delay: assert only twice-occurring differences are reported, the verdict is labeled double-compare with both pass timestamps, and a scripted between-pass mutation appears in neither final result (the documented heuristic limit, observed). (4) On a Mode 1 stream, run the cycle-flush variant and assert the second pass waited for a complete capture-and-integrate cycle. (5) Pin a pass as-of a recorded SCN; assert the as-of in the report and verdict agreement with the oracle evaluated at that position.
**Expected:** Counts tier exact and cheapest; filters honored, named, and reversible; double-compare intersection and labeling per spec including the heuristic's documented blind spot; cycle-flush waits provably; as-of pinning recorded and oracle-consistent.
**Evidence:** Timed run records, filtered/unfiltered report pair, double-compare reports with timestamps, mutation-case audit, cycle-wait timeline, pinned-pass report vs oracle.

## 12. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| CMP-01 | Verified-identical data yields zero differences from bulk, row-wise, and composed compare |
| CMP-02 | Every seeded difference is found and correctly classified, matching an external oracle exactly; nothing unseeded is reported |
| CMP-03 | One hour of online compares under full-rate replication confirms zero false positives while catching an injected real difference |
| CMP-04 | Repair from a report converges the target (re-compare clean) with writes proportional to differences |
| CMP-05 | Bulk block localization is exact and all methods agree, including on hash-collision fixtures |
| CMP-06 | The heterogeneous type-gap corpus compares clean per the published canonicalization table, while real mutations in every type family are still caught; verdicts are identical with read and write sides swapped |
| CMP-07 | Exclusions and tolerances are honored, recorded in the report, and never mask unrelated differences |
| CMP-08 | Scheduled compares alert on drift within one cycle with linked, retained reports; a killed compare resumes to an identical report |
| CMP-09 | The daily sync report's every figure (rows, columns, match rate, activity, verdict) matches external ground truth across in-sync, drifted, and structure-mismatch streams |
| CMP-10 | Reports deliver identically to UI, email, webhook, and file drop; the file-drop path works fully air-gapped with zero egress |
| CMP-11 | On-demand compares emit the identical report format from UI and CLI and are archived alongside scheduled reports |
| CMP-12 | Structure mismatches short-circuit data compare with the discrepancy named; declared extras pass, undeclared extras flag |
| CMP-13 | Direct file compare produces an oracle-exact inventory via sliced prereaders with encrypted, cleaned intermediates; unsupported stream styles are refused as documented |
| CMP-14 | Multi-target compare reads the source once and delivers independent per-target verdicts |
| CMP-15 | The counts-only tier is exact and cheapest; class filters are honored, named, and reversible; the double compare reports the two-pass intersection with honest labeling and provable cycle-flush waits; as-of pinning is recorded and oracle-consistent |

## 13. Open Questions

The re-check window policy for online compare on high-latency streams (how long to wait for in-flight resolution before confirming) needs a default and a per-compare override. Whether block checksums should be persisted per table to enable incremental compare (only re-hash blocks whose data changed since the last run — a large-table cost win) is a v1.x design candidate. Report retention defaults for regulated deployments (align with audit-package cycles) need field input. Very large difference sets need a report noise policy (full inventory vs sampled examples with counts) before the daily report ships. The Parquet direct-compare timeline (Arrow reader maturity) needs a v1.x milestone decision. Whether the sync report should support a consolidated all-streams digest (one email per hub per day) is a likely early customer request — design the per-stream format so digestion composes.
