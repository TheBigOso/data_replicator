# Sizing — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design; the model behind ARC-13's "published sizing guidance" deliverable
**Companion tool:** Replication_Scope (`C:\Users\ryanr\OneDrive\Documents\Replication_Scope`) — the calculator that implements this model

---

## 1. Purpose and Positioning

Every replication vendor publishes a sizing page; almost none publish the *model* behind it, so customers get a tier table and a prayer. This specification does both: the resource model (what actually consumes CPU, memory, disk, and IOPS on each machine class, and why), the tier guidance derived from it, and — the differentiator — a **calculator** that applies the model to the customer's actual schema and change rates. Replication_Scope already computes per-table storage footprints across eight database families and groups tables into balanced stream groups; this specification defines its second job: sizing the hub and agents from those same inputs. HVR's Hub and Agent Disk Requirements pages are the parity sources; their numbers are adopted where our architecture matches and corrected where it doesn't.

## 2. What Lives Where — the hub storage inventory

The hub is deliberately thin (architecture spec: orchestration, relay, state — never row-data-at-rest beyond the file log). Its storage holds exactly four things, each with a distinct growth law:

**The file log** — the dominant and only *unbounded-by-default* consumer. Compressed change files accumulate between capture writing them and the *last* subscribed integrate acknowledging them; steady state is small, but a held consumer grows it linearly at the compressed change rate. This is why ARC-13 exists: an explicit per-hub quota with warning → throttle → admission-refusal thresholds and a continuously exposed time-to-quota forecast, replacing HVR's guidance of "start with at least 10 GB, but possibly more." The sizing formula is the quota formula: `file_log_budget = compressed_change_rate × tolerated_consumer_outage × safety_factor`, with compression measured (the platform's own byte-I/O and compression metrics), defaulting to HVR's field observation of 5–10× until measured.

**The repository** — metadata, job/event/run records, and metrics. Modest: 20 GB covers virtually any single hub (HVR's number, kept — our repository is the same shape), with the metrics series as the only meaningful grower, governed by its retention policy. Local PostgreSQL is the recommended placement for the same reason HVR gives: a remote repository adds a failure mode that stops every pipeline when the connection drops.

**Run state and logs** — capture checkpoints, run logs, event ledger. Small but **IOPS-hot**: on a busy source, change files land every second or two with checkpoint updates at the same cadence, multiplied by channel count. This is a many-small-writes profile; the disk guidance is SSD (or an equivalently cached subsystem), sized for IOPS before capacity. Kept from HVR verbatim because the physics are identical.

**The installation** — under 1 GB, static.

**What is absent, on purpose:** refresh and compare data never persist on the hub (pass-through relay, same as HVR — kept); and HVR's **metering storage tax does not exist here** — no consumption pricing means no resync-detection samples at up to 50 MB *per table per source/target pair*, a line item that on a 500-table broadcast channel is real disk. Flat licensing is also a sizing simplification.

## 3. Compute — where the work actually happens

The architecture pushes heavy processing to the agents, so the hub's per-job CPU cost is low and flat: relay I/O plus per-hop cryptography (the hub decrypts and re-encrypts between hops — the one hub CPU cost that scales with throughput, stated because HVR states it and it's true here too). Agent-side is where sizing attention belongs, and section 4 gives it its own model. Co-locating an agent on the hub machine is a supported deployment, and it is exactly the case where the hub must be sized as hub-plus-agent; the tier table carries the same four role columns HVR's does for this reason.

## 4. Agent Sizing

### 4.1 Capture agent (source side)

**What consumes what.** During CDC the agent reads the transaction log, parses it, and holds in-flight transactions in memory until a spill threshold; during refresh and row-wise compare it reads, compresses, encrypts, and streams — deliberately never touching disk (pass-through, intermittent, with the matching *database session* often the real resource consumer). Activation adds brief metadata queries and supplemental-logging DDL. The published operating envelope, adopted from HVR's field numbers pending our own benchmarks (SIZ-05):

- **CPU:** log parsing is the hottest path — up to one full core per parser when catching up from behind; far below that when tail-reading a current log. **One parser per database log thread** — each Oracle RAC node is a thread, so a 4-node RAC sizes as four parser cores of headroom. After parsing, compression is the main CPU consumer; it is a structured setting with the trade-off stated (disable → agent CPU down, network up on both hops). Real-world reference point: under 10% of total system resources during steady CDC on a co-hosted source, typically under 5% — a number we re-earn on our stack before publishing.
- **Memory:** in-flight transaction state, bounded by a **per-transaction memory threshold** (HVR's default 64 MB per transaction per channel, adjustable both directions — kept as a structured setting with the same default until benchmarks argue otherwise). Beyond the threshold, transactions spill to the agent's bounded spool as compressed files.
- **Storage:** the static binary plus the spool area. Idle-state usage is near zero; the spool exists for exactly two cases — the memory threshold (large batch transactions committing late) and hub-unreachable buffering — both under the agent spec's explicit spool budget. Starting guidance: 5 GB, grown by the calculator when the workload profile says so (long-running batch shops need more; see the long-transaction note below). Compare spill shares the same governed area.
- **I/O:** tail-of-log reads per channel, every second or two — cache-absorbed on modern storage, listed because many channels on legacy storage can contend.
- **Long-running transactions:** the capture engine periodically checkpoints its in-memory transaction state to disk so that recovery never requires re-reading archived logs from the start of the oldest open transaction (HVR's Oracle practice, adopted as a general design rule). Shops with hours-long batch transactions size the spool for these state snapshots; the calculator takes "longest routine transaction" as an input.

### 4.2 Integrate agent (target side)

**What consumes what.** Apply work splits by mode: continuous integration is cheap per row; **burst coalescing** — reducing each row's changes to one net operation per cycle — is the expensive path, CPU-heavy and *memory-heavier*, spilling to disk past its threshold. Row-wise compare on the target side may sort the retrieved data — memory-intensive with spill **up to the full data-set size**, the single largest transient disk demand on any agent. The published envelope:

- **CPU:** the agent itself is light; the *database session* it drives can absorb a full core per integrate process (more under parallelism), and MPP bulk loaders where used (Teradata TPT, Greenplum gpfdist class) are resource-intensive client utilities that must be sized on this machine even though they aren't our process — HVR's warning, kept verbatim because it bites.
- **Memory:** under 1 GB per integrate in steady state; gigabytes transiently during row-wise compare/refresh — intermittent by nature.
- **Storage:** temp area for coalesce spill and compare/refresh sort spill — starting guidance 5 GB, with the row-wise-sort worst case (≈ largest table's compared volume) as the calculator's sizing driver for compare-heavy deployments.
- **Scale-out:** consolidation topologies funnel many sources through one integrate agent — the natural bottleneck. Multiple integrate agents behind a load balancer is the HVR pattern; our v1 answer is per-channel agent assignment (spread channels across agents), with dynamic scale-out of a single channel's integrate an explicit open question.

**Out of v1 scope, stated:** SAP cluster/pool table decoding (HVR's SAP Transform) is not carried in v1 — a roadmap candidate given the defense-manufacturing installed base, recorded in the open questions rather than implied.

## 5. The Tier Table

Change rate means the volume of transaction-log change the source produces, whether or not the channel captures all of it (the parser reads the log either way — HVR's definition, kept). Tiers adopted from HVR's field-validated table as the starting guidance, to be re-benchmarked on our stack before the numbers are published as ours (SIZ-02):

| Tier | Resources | Standalone hub | Hub + capture agent | Hub + integrate agent | Hub + both |
|---|---|---|---|---|---|
| Small | 4–8 cores · 16–32 GB · 50–500 GB SSD · 10GigE | ~5 channels @ ≤20 GB/h | ~2 channels @ ≤20 GB/h | ~2 channels @ ≤20 GB/h | 1 channel @ ≤20 GB/h |
| Medium | 8–32 cores · 32–128 GB · 300 GB–1 TB SSD · 2×10GigE | ~20 channels, ≤5 @ 100 GB/h | ~8 channels, ≤2 @ 100 GB/h | ~6 channels, ≤2 @ 100 GB/h | ~4 channels, ≤2 @ 100 GB/h |
| Large | 32+ cores · 128+ GB · 1 TB+ SSD · 4+×10GigE | 50+ channels | 15+ channels | 12+ channels | 8+ channels |

The table is guidance; the calculator is the product. A tier row cannot know your outage tolerance, your compression ratio, or that one of your five channels is an eight-node Exadata — the calculator takes those as inputs.

## 6. Replication_Scope — the calculator

The tool's existing layer (per-table footprint from schema across Oracle/SQL Server/Synapse/HANA/MySQL/MariaDB/PostgreSQL/SQLite; ranking; stream groups) already answers the *initial load* questions: total refresh volume, per-group volume, and load balance. The environment-sizing layer adds, per scenario:

**Inputs:** the loaded tables (already there), per-table or per-group change rates (the parked CDC throughput model — per-table changes/sec with insert/update/delete mix — is precisely this input, so the `CDC_ENABLED` flag's future release is the sizing release), channel/topology layout (which stream groups feed which targets), tolerated consumer-outage window, tolerated hub-outage window, longest routine transaction, compression ratio (default 5–10× band until measured), agent co-location and RAC/thread counts, and metrics retention.

**Outputs:** recommended hub tier (role column applied), the **file-log quota recommendation** with warning/throttle thresholds (the exact ARC-13 settings), per-source capture sizing (parser-core headroom from thread count, memory-threshold guidance, spool budget from outage window and longest transaction), per-target integrate sizing (coalesce memory, compare-sort worst-case temp), repository allocation with metrics-retention sensitivity, and an IOPS estimate from change-file cadence × channel count. Every output shows its formula and inputs inline — the calculator obeys the same nothing-hidden rule as the product, so a customer can argue with the model rather than trust it.

**One model, two artifacts:** the formulas in this specification and the formulas in Replication_Scope are kept identical by shared golden test vectors (SIZ-03) — a scenario file with known inputs and hand-computed outputs, versioned in both repos. If the spec's model changes, the tool's tests fail until it follows, and vice versa.

## 7. Monitoring and the Operational Loop

HVR's guidance is threshold alerts at 80/85/90% disk with ">90% is a production support call." Ours is the ARC-13 machinery: quota-relative thresholds (warning, throttle, admission refusal) plus the **time-to-quota forecast** computed from live ingress/egress rates — "you will hit the wall Thursday at 2 AM" beats "you are at 85%." Agent spool budgets carry the same treatment (the agent spec's budget alerts). Repository capacity rides the upgrade-preflight check (ARC-14) and ordinary DB monitoring. The sizing loop closes operationally: the calculator's predicted rates vs the hub's measured rates are both visible, so a deployment that outgrows its scenario is a report, not a surprise.

## 8. HVR Parity Matrix

| HVR sizing concept | This platform | Delta |
|---|---|---|
| Hub limited to orchestration, state, temporary router files; refresh is pass-through | Same shape: hub never persists row data beyond the file log | Kept — the thin-hub principle |
| "Start with at least 10 GB, possibly more" for transaction-file accumulation | Explicit quota + thresholds + time-to-quota forecast (ARC-13); budget formula published | Hope replaced by arithmetic |
| Metering/resync samples: up to 50 MB per table per source/target pair | Does not exist — no consumption metering | Storage tax removed by the license model |
| Heavy processing on agents; hub CPU low; hub re-encrypts per hop | Same distribution; per-hop crypto cost stated | Kept, stated |
| Log parsing up to 1 core per parser; one parser per log thread / RAC node | Same model; parser-core headroom computed from thread count by the calculator | Kept, calculated |
| 64 MB per-transaction memory threshold, adjustable, spill beyond | Same default as a structured setting; spill into the bounded spool | Kept; spill governed by budget |
| Capture <10% (typically <5%) of co-hosted system during steady CDC | Adopted as the reference envelope; re-earned by our benchmarks before publication | Kept, to be re-validated |
| Oracle memory-state checkpoint to avoid archived-log re-reads | Adopted as a general capture design rule; spool sized for it via the longest-transaction input | Kept, generalized |
| Compression on by default; disable = CPU↓ network↑ | Structured setting with the trade-off stated | Kept |
| Burst coalesce CPU/memory heavy with spill; row-wise sort spill up to data-set size | Same physics; calculator sizes temp from the compare-sort worst case | Kept, sized honestly |
| MPP loader utilities (TPT/gpfdist) resource warning | Kept verbatim per connector in the capability matrix | Kept — it bites |
| Integrate scale-out via load balancers for many-to-one | v1: per-channel agent spread; single-channel dynamic scale-out is an open question | Partially kept, honestly scoped |
| SAP Transform (cluster/pool decoding) on integrate agent | Not carried in v1; roadmap candidate | Honest absence |
| Agent storage: start 5 GB both sides | Same starting guidance under explicit budgets, grown by calculator inputs | Kept, governed |
| 5–10× compression reduces transfer | zstd measured per deployment via compression metrics; 5–10× as the unmeasured default band | Kept; measured over assumed |
| Tier table (Small/Medium/Large × four hub roles) | Adopted as starting guidance; re-benchmarked before publication as ours | Kept, to be re-validated (SIZ-02) |
| Repository ≤20 GB; local placement preferred; stats dominate growth | Same, with metrics retention as the governed grower | Kept |
| Disk alerts at 80/85/90% | Quota-relative warning/throttle/refusal + forecast, on hub and agent spools alike | Thresholds kept, forecast added |
| Sizing pages only | Sizing model + calculator applying it to the customer's schema and rates | The differentiator |

## 9. Test Plan

Phased; standing rule applies. SIZ criteria are also the evidence backing ARC-13's "published sizing guidance" release gate — this plan is how that guidance earns its numbers.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Model vs measurement | SIZ-01, SIZ-05 | Lab hub + agents + TPC-C at calibrated change rates | Metrics pipeline implemented | Hub and agent predictions within stated tolerance of measurement |
| B | Tier validation | SIZ-02 | Lab at tier-boundary loads | Phase A exit | Published tier numbers demonstrated at their boundaries |
| C | Calculator conformance | SIZ-03 | Replication_Scope test suite + spec vectors | Sizing layer implemented in the tool | Golden vectors pass in both repos |
| D | Operational loop | SIZ-04 | Lab pressure drill (with ARC-13) | Phases A–C | Forecast accuracy and threshold behavior proven |

## 10. Test Procedures

### SIZ-01 — Hub model accuracy against measured consumption
**Steps:** (1) Run TPC-C at three calibrated change rates (low/mid/high) through a standard channel for a sustained window each. (2) Record measured values: compressed bytes/hour on the hub store, file-write cadence (IOPS), repository growth, hub CPU. (3) Compute the model's predictions from the same inputs (schema via Replication_Scope, measured compression ratio, rates). (4) Compare, per resource, against the stated tolerance (tolerance itself is published with the model).
**Expected:** Every predicted figure within tolerance of measurement across all three rates; deviations investigated, and either the model or the tolerance is corrected before publication.
**Evidence:** Measurement series, prediction worksheets, deviation table.

### SIZ-02 — Tier boundaries demonstrated
**Steps:** (1) On hardware matching the Small tier spec, run the Small standalone-hub boundary load (5 channels at 20 GB/h change rate) for a sustained window; assert stability: latency flat, no threshold crossings, CPU/memory within envelope. (2) Push 1.5× the boundary and record where the machine degrades (headroom characterization). (3) Repeat for the hub-plus-capture-agent column. (4) Medium tier: the high-rate cell (channels at 100 GB/h) on Medium hardware.
**Expected:** Published boundary loads run stably on their tier hardware; degradation beyond boundary is characterized, not mysterious; the published table's numbers are ours by demonstration, not inheritance.
**Evidence:** Sustained-run metric series per cell, degradation curves.

### SIZ-03 — Calculator/spec conformance via golden vectors
**Steps:** (1) Maintain the golden scenario: a fixed table set (the tool's five-table sample extended with change rates), fixed assumptions, and hand-computed expected outputs (quota, tier, capture and integrate sizing, repository, IOPS) — versioned in both this repo and Replication_Scope. (2) Run the vector through the tool's test suite (`npm test`) and through the spec's worksheet independently. (3) Any model change must update the vector in both places; CI in the tool repo fails on divergence.
**Expected:** Identical outputs from tool and spec on every vector; a deliberate model tweak in one repo fails the other's check until reconciled.
**Evidence:** Vector file hashes, both test outputs, one demonstrated divergence-and-reconcile cycle.

### SIZ-04 — Forecast accuracy and threshold drill
**Steps:** (1) With quota configured from the calculator's recommendation, hold a consumer (ARC-13's drill) and record the time-to-quota forecast at onset. (2) Let pressure build to the warning threshold; compare forecast-predicted wall-clock against actual. (3) Verify the calculator's recommended thresholds produced warning before throttle before refusal with operationally useful spacing (documented minimum lead time). (4) Release, drain, and verify the post-incident report shows predicted-vs-actual rates.
**Expected:** Forecast within its stated accuracy band; threshold spacing per recommendation; the sizing loop's predicted-vs-measured view populated.
**Evidence:** Forecast-vs-actual timeline, threshold event sequence, loop report.

### SIZ-05 — Agent resource envelope
**Steps:** (1) Capture: run steady tail-reading CDC at the mid calibration rate; record parser CPU per channel (must sit well under one core) and total agent share of a co-hosted system (compare against the published envelope). (2) Force catch-up from a two-hour log backlog; assert the parser saturates at ~one core per log thread and no more (run once against a two-thread source fixture: two cores, not three). (3) Drive a single 500 MB batch transaction; assert memory holds to the per-transaction threshold, spill engages beyond it as compressed files within the spool budget, and capture completes and resumes cleanly. (4) Integrate: run a burst cycle over a coalesce-heavy change mix; record memory and spill against the model. (5) Row-wise compare on the largest lab table from the target agent; record sort spill peak vs the calculator's worst-case prediction. (6) Disable compression on one channel; measure the agent-CPU-down/network-up trade against the stated guidance.
**Expected:** Every measured envelope within the published tolerance of the model's prediction; thread-count scaling exact; spill bounded by budgets with clean resume; the compression trade-off as documented.
**Evidence:** Per-step metric series, spill audits, thread-scaling observation, trade-off measurements.

## 11. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| SIZ-01 | The published sizing model predicts measured hub resource consumption within its stated tolerance across three calibrated change rates |
| SIZ-02 | Published tier-table boundary loads run stably on tier-spec hardware, with beyond-boundary degradation characterized |
| SIZ-03 | Replication_Scope and this specification produce identical outputs on shared golden vectors, with cross-repo divergence failing CI |
| SIZ-04 | Quota and threshold settings recommended by the calculator produce accurate time-to-quota forecasts and correctly spaced warning/throttle/refusal behavior in a live pressure drill |
| SIZ-05 | Agent envelopes hold as published: parser cores scale exactly with log threads, the per-transaction memory threshold governs spill into budget with clean resume, coalesce and compare-sort spill match predictions, and the compression trade-off behaves as stated |

## 12. Open Questions

The tolerance bands for SIZ-01/SIZ-05 (per resource class) need lab data before they can be stated honestly — publishing them is part of the model. Whether the calculator should model network (the tier table's line-rate column) or treat it as a checklist item needs a decision; change-rate × compression gives the number cheaply. Single-channel integrate scale-out (beyond per-channel agent spread) for heavy consolidation topologies is an architecture question for v1.x. SAP cluster/pool table decoding (HVR's SAP Transform equivalent) is a roadmap decision with real pull in the defense-manufacturing base. Per-connector agent benchmarks (capture parse cost per source family; integrate load cost per target family) feed the v1.x agent sizing table. Repository placement guidance for HA deployments (local vs the standby-hub shared-repository pattern) ties into the v2 hub-HA design.
