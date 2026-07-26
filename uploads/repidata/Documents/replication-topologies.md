# Replication Topologies — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 verdicts locked; bidirectional design pass scheduled for v2

---

## 1. Purpose and Positioning

HVR markets six replication topologies as capabilities. The architectural insight driving this specification is that four of the six are not features to build — they are emergent properties of a log-shipping transport designed with multi-consumer acknowledgment from day one. By deciding transport before topology (rather than the reverse), this platform ships the same six-picture story while only engineering two of them.

## 2. Topology Verdicts

### 2.1 Uni-directional, one-to-one (v1, free)

The base case: one pipeline, one source, one target. Everything in the architecture document describes this path.

### 2.2 Broadcast, one-to-many (v1, free by design)

One capture, N targets. Change files are relayed from the hub to every subscribed integrate agent; garbage collection waits for all consumers' acknowledgments (ack-based GC). Capture-once-deliver-many — e.g., one Oracle capture feeding Snowflake for analytics and S3 for the data lake — falls directly out of the file log with no additional engineering. Typical uses: distributing load across identical systems, feeding a warehouse and a lake from a single source read.

### 2.3 Consolidation, many-to-one (v1, cheap)

N pipelines into one target — the data-warehouse consolidation pattern (branch systems feeding a central analytics database). The engine requires only "politeness" work: per-pipeline state tables so exactly-once tracking never collides; schema and naming mapping so sources land without conflict; and concurrency control on burst apply so simultaneous integrates into one target do not contend pathologically. Configuration pattern plus modest engineering.

### 2.4 Cascading (v1, free by composition)

A target that is also a source: integrate applies changes as ordinary transactions; capture on that database reads them from its log like any other writes; the next pipeline carries them onward. Classic use: source → warehouse → per-department data marts. The engine needs nothing special. Two supporting requirements: the UI's topology view must render chains legibly (see UI screens scope), and the change-origin lineage must append correctly at each hop so the full path remains traceable back to hop-0.

### 2.5 Bi-directional, active/active, two nodes (v2, real work)

Both sides accept application writes and stay in sync — geo-distributed apps, high-availability pairs. Two mechanisms are required and both get a dedicated design pass before implementation:

Loopback detection. The platform must not re-capture its own applied changes (the boomerang problem). The design hook already exists: the integrate agent updates its state table in the same transaction as the data, giving every applied transaction a natural, free marker; capture recognizes transactions bearing the marker (or performed by the integrate service account touching the state table) and skips them. The change-origin lineage in the file format provides defense in depth and cross-hop identification (loopback needs only the chain's most recent entry).

Collision detection and resolution. When both sides modify the same row inside the replication latency window, the conflict must be detected (before-image comparison against current target state) and resolved by a configurable policy (timestamp-wins, site-priority, or route-to-queue for manual resolution), with every collision logged as a first-class event. Resolution policy is per-channel.

### 2.6 Multi-directional, n-way active/active (deferred, deliberately)

More than two nodes in full mesh sync. Honest assessment: this topology sells demos and generates support escalations. N-way conflict resolution across geo-distributed nodes under variable latency is a product unto itself, represents a small fraction of real deployments, and accounts for a disproportionate share of GoldenGate and HVR field pain. The intent is documented; implementation waits for a paying customer whose requirement survives scrutiny. The v1 file format (origin markers) and the v2 bidirectional mechanisms are designed so n-way is an extension, not a rewrite.

## 3. The v1 Requirement Hiding in a v2 Feature

The change-origin lineage — an ordered chain of (location, channel) entries, hop-0 first, appended per hop — must ship in the very first file-format version. It is a chain, not a scalar, and that distinction is resolved now rather than discovered later: loopback detection needs only the most recent hop, but cascading lineage (TOP-03) and future n-way replication need the full ordered path back to hop-0, and adding a field to a shipped, published file format is a versioned migration. The encoding keeps the cost at a few bytes per record regardless of depth (dictionary-indexed varints against a per-file origin dictionary; depth bounded at 16 with a loop-suspected failure at the bound — see architecture spec 3.3). This is recorded in the architecture document as a v1 core commitment.

## 4. HVR Parity Matrix

| Topology | HVR 6 | This platform |
|---|---|---|
| Uni-directional | Yes | v1 |
| Broadcast | Yes | v1, emergent from ack-based GC |
| Consolidation | Yes | v1, per-pipeline state isolation |
| Cascading | Yes | v1, composition + origin lineage |
| Bi-directional | Yes (loopback + collision detect/resolve) | v2, dedicated design pass |
| Multi-directional | Yes | Deferred, demand-driven |

## 5. Test Plan

Phased plan; the standing rule applies (procedure executed, results observed, evidence archived — no procedure, no pass), and the full suite reruns as regression on every merge touching this area.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | v1 compositions | TOP-01, TOP-02, TOP-03, TOP-04, TOP-07 | Integration lab, multi-endpoint harness | Broadcast/consolidation/cascade configurable | All pass; GC-hold, isolation, and lineage proven |
| B | Bidirectional (v2) | TOP-05, TOP-06 | Soak harness + collision injector | v2 loopback/collision implemented | 1M-change soak clean; all policies proven |

### 5.1 Methods

Topology tests compose the lab's single-pipeline harness into multi-endpoint arrangements and verify the emergent properties actually emerge.

**Broadcast** stands up one capture with two heterogeneous integrates (Postgres + file target in the lab tier); a throttle on one consumer creates the slow-target condition for GC-hold verification (TOP-01). **Consolidation** runs three TPC-C sources into one target with deliberate table-name collisions in the fixture set to prove configuration-time rejection (TOP-04), and kills one pipeline mid-run to prove state-table isolation (TOP-02). **Cascading** chains two lab pipelines and compares hop 2 against hop 0, asserting origin markers at each hop via file-log inspection (TOP-03). **Topology-view rendering** (TOP-07) is verified by the same Playwright infrastructure that captures documentation screenshots, driving the UI against live repository state for each arrangement.

**Bidirectional (v2)** adds a soak harness: two Postgres nodes with bilateral write generators running a 1M-change soak, asserting zero loopback re-application by origin-marker accounting (TOP-05), plus a collision injector that writes the same rows on both sides inside the latency window and asserts detection, policy-correct resolution, and event logging for each configured policy (TOP-06). Multi-directional has no test obligation until it leaves deferred status — by design.

## 6. Test Procedures

Compact procedures; each follows preconditions → steps → expected → evidence. A criterion passes only with its evidence archived in the run record.

### TOP-01 — Broadcast with slow-consumer GC hold
**Preconditions:** Lab capture (Postgres TPC-C) broadcasting to targets T1 (Postgres) and T2 (file target); bandwidth throttle available on T2's integrate.
**Steps:** (1) Run TPC-C for 20 minutes with T2 throttled to ~10% of T1's rate. (2) Sample hub file-log inventory every 2 minutes, recording oldest unacked sequence per consumer. (3) Remove the throttle; let T2 catch up. (4) Run compare source-vs-T1 and source-vs-T2.
**Expected:** During throttling, files past T1's ack but before T2's ack are retained (never GC'd); after catch-up, GC advances to the joint low-water mark; both compares clean.
**Evidence:** File-log inventory samples, GC advance log, both compare reports.

### TOP-02 — Consolidation isolation under pipeline failure
**Preconditions:** Three TPC-C sources (S1–S3) consolidating into one Postgres target with per-pipeline state tables.
**Steps:** (1) Run all three under load 10 minutes. (2) Kill S2's capture agent; continue 10 minutes. (3) Restart S2; let it drain. (4) Compare each source against its target schema.
**Expected:** S1/S3 unaffected throughout (latency metrics flat); S2 resumes from checkpoint; three clean compares; state tables show independent positions at every sample.
**Evidence:** Latency series for S1/S3, state-table snapshots, compare reports.

### TOP-03 — Cascading chain with origin lineage
**Preconditions:** Chain S → M (Postgres) → T; file-log inspection tool.
**Steps:** (1) Run TPC-C on S for 15 minutes. (2) Inspect hop-1 and hop-2 change files: decode origin markers on a 1,000-record sample per hop. (3) Compare T against S.
**Expected:** Hop-1 records carry a single lineage entry identifying pipeline S→M; hop-2 records carry the ordered two-entry chain — the original S→M entry first, the M→T entry appended — per the format spec; end-to-end compare clean.
**Evidence:** Decoded marker samples, compare report.

### TOP-04 — Consolidation naming collision at config time
**Preconditions:** Two source fixtures each containing table `ORDERS` targeting the same target schema without mapping.
**Steps:** (1) Configure pipeline 1 (succeeds). (2) Attempt pipeline 2 with the colliding table and no rename mapping. (3) Add a rename mapping and retry.
**Expected:** Step 2 is refused at configuration time with a message naming both pipelines and the colliding object; step 3 succeeds; no job ever launched in the failing case.
**Evidence:** Refusal message capture, event log showing zero job starts.

### TOP-05 — Bidirectional loopback soak (v2)
**Preconditions:** Postgres pair A↔B in bidirectional channel; bilateral write generators (disjoint key ranges); origin-marker accounting tool.
**Steps:** (1) Soak 1M changes per side. (2) Account every applied transaction on each side by origin. (3) Compare A vs B.
**Expected:** Zero transactions applied on the side that originated them (no boomerang); row counts reconcile exactly; compare clean.
**Evidence:** Origin accounting totals, compare report.

### TOP-06 — Collision detection and policy resolution (v2)
**Preconditions:** Bidirectional pair; collision injector writing the same keys on both sides within the latency window; each policy (timestamp-wins, site-priority, route-to-queue) configurable per run.
**Steps:** For each policy: (1) Inject 100 seeded collisions. (2) Verify detection count, resolution outcome per policy, and event records containing both images. (3) For route-to-queue, resolve two manually and verify application.
**Expected:** 100/100 detected each run; outcomes match policy exactly; every collision logged with both before-images; manual resolutions apply cleanly.
**Evidence:** Collision event exports, per-policy outcome tallies.

### TOP-07 — Topology view rendering
**Preconditions:** Live repository containing one broadcast, one 3-source consolidation, and one 2-hop cascade; Playwright harness.
**Steps:** (1) Drive the topology view for each arrangement. (2) Assert every location, pipeline, and direction is present and correctly connected in the rendered DOM. (3) Capture screenshots (feeding the docs pipeline).
**Expected:** All three render with correct structure; no truncated or overlapping elements at default viewport.
**Evidence:** Playwright assertions, archived screenshots.

## 7. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| TOP-01 | Broadcast to two heterogeneous targets: both receive the identical change stream; compare verifies both against source; GC holds until the slower target acknowledges |
| TOP-02 | Consolidation of three sources into one Postgres target: state tables remain isolated per pipeline; kill and resume one pipeline without disturbing the other two |
| TOP-03 | Cascading two-hop chain delivers end-to-end with correct origin markers at each hop; compare verifies hop 2 against hop 0 |
| TOP-04 | Consolidation naming collision (same table name from two sources) is caught at configuration time, not runtime |
| TOP-05 | (v2) Bidirectional pair under concurrent bilateral writes: zero loopback re-application over a 1M-change soak run |
| TOP-06 | (v2) Seeded write-write collision is detected, resolved per configured policy, and logged as an event with both images |
| TOP-07 | Topology view renders a broadcast, a consolidation, and a two-hop cascade legibly from live repository state |

## 8. Open Questions

Whether cascading hops should optionally filter by origin (to exclude replicated-in rows from onward replication) needs a per-channel switch decision in the v2 design pass. Collision resolution policy defaults per industry (site-priority for defense HA pairs vs timestamp for geo apps) to be decided with early customers.
