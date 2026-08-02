# Compare — Console Surface

**Project:** Enterprise CDC Replication Platform
**Document type:** UI design specification
**Status:** v1 design, prototyped in `Replicator UI.dc.html`; wireflow in `Compare Data Wireflow.dc.html`
**Companion concepts:** `compare.md` (methods, canonicalization, online truth, the report), `refresh.md` (repair engine), `slicing-design.md` (slice machinery), `run-history.md` (ledger handoff), `jobs.md`, `events.md`

This document specifies the operator-facing compare surface: the dialog, the running job, the deep-analysis drill-in, the background lifecycle, the results report, and repair. `compare.md` owns the semantics; this owns the console.

---

## 1. Entry points and gates

Compare is scoped to one stream. Entry points: **Stream detail → Compare**, **Stream admin → Run compare**, and **Repeat** on a COMPARE event in the ledger.

- A stream with **no registered tables** never opens the dialog — a toast says to register tables first.
- A stream that **already has a compare running or a report open** reopens that window instead of starting over (one compare per stream; different streams run concurrently).

## 2. The dialog — setup

One window, three phases (setup → running → results).

**Scope.** The stream's capture connection is the read location and its apply connection the write location, shown as `SOURCE ≈ TARGET` — fixed, not pickable. Stated inline: both sides canonicalize to the same comparison form, so swapping read and write cannot change the verdict. Below, the stream's registered tables as a checklist with select-all (all selected by default).

**Method — three tiers** (compare.md §2), radio cards:

| Tier | Says | Cost |
| --- | --- | --- |
| Row counts only | COUNTS EQUAL / COUNT MISMATCH — no classes, no repair | cheapest |
| Bulk — checksums only | IDENTICAL / DIFFERENT, per block — not which rows | one scan per side, checksums travel |
| Composed (default) | full row inventory on the differing blocks; enables repair | bulk + row-wise where needed |

**Options.**
- **Online compare** — in-flight window re-check (default) or double compare with a wait (labeled a persistent-difference *filter*, per compare.md §4.1). Disabled for the counts tier.
- **Parallel sessions** — 1/2/4/8 tables at once.
- **Only count certain differences** — no-inserts / no-deletes / no-updates class filters; always named in the report.
- **Restrict** — optional predicate applied to both sides, recorded in the report.
- **CLI equivalent** — a live `repl compare …` line mirroring every option (UI/CLI parity rule).

Gate: at least one table selected.

## 3. Running — the job

Starting a compare logs a **COMPARE event (state CURRENT)** with every setting, and holds a job `<stream>-cmp` for as long as the event is CURRENT. A composed run is paced at **~3–4 minutes** (counts/bulk proportionally quicker).

The run view shows: overall progress bar with elapsed time; the **phase list** — structure check → source scan → target scan → row-wise on differing blocks (composed only); and a per-table list with phase label, mini progress bar, and PENDING/BUSY/DONE pill. Footer actions: **Run in background** and **Cancel event**.

## 4. Deep analysis drill-in

Clicking a table row expands its deep analysis (the slice machinery of `slicing-design.md`):

- **Slice map** — "Slice 144 of 156", slices complete, plus "56% done with slice 145" on a second bar.
- **Current operation** — what the engine is doing right now, with the key range and slicing column ("keys 1,440,000 … 1,450,000 — modulo on AP_INVOICE_ID").
- **Positions** — read SCN vs applied-through position, and throughput (rows/s).
- **Per-session assignments** — one chip per parallel session with its slice and progress.

Closing the drill-in (or the window) never affects the job.

## 5. Background lifecycle

Long compares must not hold the operator hostage:

- **Close = background.** "Run in background" or ✕ closes the window; the job keeps running. Several compares (one per stream) plus event-driven refreshes and repairs run concurrently.
- **Notice chip** (bottom-right, everywhere in the console) aggregates everything in flight — "3 background jobs running · ora-erp-cmp 62% · pg-billing-rfr 41% …". Click → Jobs.
- **Jobs rows expand** for running event-driven work: overall bar, phase line ("scanning target · 62%", "row-wise apply — slice 14 of 33"), per-table % chips for compares. **Open window** reopens the compare dialog mid-run.
- **Completion:** the job leaves the Jobs list, the event flips CURRENT → DONE (persisted), a toast states the verdict, and the chip offers the report. The stream's Compare button also reopens a finished report.
- **Cancel** (run view or Events) drains the job; the event is CANCELED and repeatable.
- **Reload rule:** a compare that was CURRENT when the page unloaded cannot resume — it is marked CANCELED at load, never left as a zombie RUNNING row.

## 6. Results — the report

Header: verdict pill — **IN SYNC / DRIFT DETECTED / STRUCTURE MISMATCH** — with tables compared / identical / different / structure counts, rows compared, duration, and (online runs) transient-resolved count. A settings echo (`source_loc / target_loc / granularity / online_compare / parallel_sessions / class_filters / restrict`) restates what the verdict was allowed to ignore.

Per-table rows: state pill, source rows, target rows, **missing on target / only on target / different**, match rate, and a **View file** diff link (RBAC'd inspection, per compare.md §5). Structure mismatches short-circuit with the column named ("column TIER missing on target") and no row numbers — never garbage diffs. Bulk/counts verdicts that name no rows get a **"Set up composed re-run"** shortcut that pre-selects only the differing tables.

## 7. Repair

Offered only from a composed report with drift (checksums and counts have no inventory to apply). The panel:

- **Direction** — source → target (source is truth, default) or target → source; labels and SQL flip with it.
- **Difference classes** — insert missing / update differing / delete extra, each with its row count; zero-count classes dimmed.
- **Restrict** — a custom WHERE clause narrowing the repair (e.g. the incident window).
- **SQL preview** — the INSERT / MERGE / DELETE statements sent to the read side, keys from the diff, restrict ANDed in.

**Create repair job** logs a **REFRESH event (CURRENT)** with direction, classes, restrict, tables, and row counts; the job runs in the same background pool, and writes are **O(differences)** — never a full reload (refresh spec REF-05). The follow-up is stated: re-compare to confirm convergence.

## 8. Job and event integration

| Moment | Jobs screen | Events ledger |
| --- | --- | --- |
| Start | `<stream>-cmp` RUNNING (n% done) | COMPARE event CURRENT, all settings in details |
| Running | row expanded with live progress | CURRENT |
| Done | row removed | CURRENT → DONE (persisted), report attached |
| Canceled | row removed | CANCELED, repeatable |
| Page reload mid-run | never resurrects | CANCELED (interrupted) |
| Repair created | `<stream>-rep` in the refresh pool | REFRESH event CURRENT → DONE |

## 9. Acceptance criteria

| ID | Criterion |
| --- | --- |
| CMPUI-01 | Compare opens scoped to the stream's read/write locations and registered tables; a table-less stream gets a toast, not a dialog |
| CMPUI-02 | All three method tiers selectable; online compare is disabled for counts; every option is mirrored in the CLI line |
| CMPUI-03 | Class filters and restrict are echoed in the report settings and in the COMPARE event details |
| CMPUI-04 | Starting a compare creates a CURRENT COMPARE event and a RUNNING job; both carry the same identity |
| CMPUI-05 | A composed run paces ~3–4 minutes with per-table progress and phase labels matching the engine order (structure → source → target → row-wise) |
| CMPUI-06 | Deep analysis shows slice n of m, % of the current slice, operation + key range, read/write positions, and per-session assignments, without affecting the run |
| CMPUI-07 | Closing the window backgrounds a running compare; multiple compares (one per stream) and refreshes run concurrently |
| CMPUI-08 | The notice chip aggregates all running background jobs with live %, and navigates to Jobs |
| CMPUI-09 | Jobs rows for event-driven work expand with live progress; Open window reopens the compare dialog mid-run |
| CMPUI-10 | On completion the job leaves Jobs and the event flips to DONE, persisted across reloads; a reload mid-run yields CANCELED, never a zombie RUNNING row |
| CMPUI-11 | Results show per-table difference classes, match rate, and diff-file access; structure mismatches short-circuit with the column named |
| CMPUI-12 | Bulk/counts drift offers the composed re-run pre-scoped to the differing tables |
| CMPUI-13 | Repair is offered only from a composed report; direction, classes, and restrict shape the SQL preview; creating it logs a REFRESH event with row counts O(differences) |
| CMPUI-14 | Cancel (run view or Events) drains the job and marks the event CANCELED and repeatable |
