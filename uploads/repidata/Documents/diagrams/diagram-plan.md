# Diagram Plan — one wire diagram per concept

**Purpose:** The transparency principle applied visually. Every concept in the document set must be explainable in one diagram; this file is the inventory that enforces it. A concept without its diagram is as incomplete as a criterion without its procedure. Diagrams live in this folder (exports) and in Lucid (editable originals); each entry names the diagram type, what it must show, and the owning spec section.

**Status legend:** ✅ exists · 🖼 wireframe captured · ⬜ to generate

---

## Architecture

1. ✅ **System Architecture** — layered zone diagram: clients → REST-only hub (scheduler, relay, file log, repository, event ledger, sync report) → capture/integrate agents → sources/targets, with mTLS/ack-GC flows and product principles. *Lucid: https://lucid.app/lucidchart/f338bdf1-f04e-45b9-9849-743b12701883/edit* (architecture.md §2–3)
2. ⬜ **Life of a Single Change** — 12-step numbered flow from redo write to dashboard latency, one lane per component, checkpoint-advance points marked (steps 6 and 9 highlighted — they are the exactly-once story). (architecture.md §4)
3. ⬜ **Non-transactional delivery** — two panels: file-target manifest cycle (write objects → atomic manifest → recovery reconcile) and Kafka transactional cycle (records + state topic in one transaction). (architecture.md §3.3)

## Topologies

4. ⬜ **Six topology thumbnails** — one-to-one, broadcast, consolidation, cascade, bidirectional (v2), multidirectional (deferred), each with its verdict badge and the origin-lineage hop chain drawn on the cascade. (replication-topologies.md)

## Connection & Agent

5. ⬜ **Reachability modes** — agent-on-host vs agentless vs agent-initiated (air-gap) connection patterns, one panel each, firewall lines drawn. (connection.md; agent.md)
6. ⬜ **Agent enrollment sequence** — UML sequence: token issue → first start → keypair → pin → mTLS established; upgrade orchestration as a second lane. (agent.md)

## Scheduler & Jobs

7. ⬜ **Three stream modes** — three lanes (continuous CDC / scheduled refresh / CDC + scheduled compare) with their job compositions and the soft-landing (SELECT-only) path marked on Mode 2. (scheduler.md)
8. ✅ **Job & Event State Machine** — the published transition diagram JOB-01 tests against: every state, every edge with its cause, HANGING as a flag on RUNNING, the two terminals with cause fields. *Lucid: https://lucid.app/lucidchart/fd094715-5f79-4f54-8570-29501a4d9d49/edit* (jobs.md §2, §4; events.md §4)

## Stream

9. ⬜ **Stream structure** — location groups, table set, table groups, and the four-level settings ladder with a provenance callout. (stream.md §2)
10. ⬜ **Creation wizard flow** — five steps as a horizontal flow, each step's validation surfaces called out, ending in the plan preview. (stream.md §5.1)
11. ⬜ **Activation sequence** — the ten-step first-activation walkthrough as a sequence diagram; the step-8 zero-downtime handshake highlighted. (stream.md §6.5)
12. 🖼 **Stream detail page** — wireframe: summary/graphs/jobs panes + management menu. *Captured: Screenshot 2026-07-12 (fleet + drill-down pair covers the pattern).* (stream.md §7)
13. ⬜ **Replication styles side-by-side** — the same DML sequence materialized through standard replica / soft delete / TimeKey, three columns, the worked example of §3.1 drawn. (stream.md §3)

## Refresh & Compare

14. ⬜ **Online handshake timeline** — position axis: snapshot S, refresh coverage ≤S, capture coverage >S, per-table boundary, integrate skip rule; the no-suspension coordination note. (refresh.md §4)
15. ⬜ **Stage-and-swap** — staging load → atomic swap → reader-visibility guarantee, with the killed-run path showing prior data intact. (refresh.md §2.1)
16. ⬜ **Compare compose funnel** — counts → block checksums → row-wise on differing blocks; classification outputs; direction-independence stated. (compare.md §2–3)
17. ⬜ **Online compare window** — in-flight window between source-read position and target applied position; re-check loop; the double-compare two-pass variant as an inset. (compare.md §4)
18. ⬜ **Sync report layout** — wireframe of the report itself: three questions, per-table grid, verdict line, trend strip, delivery sinks. This is a marketing asset as much as a spec figure. (compare.md §6)

## Slicing, Events, Security

19. 🖼 **Slice map & drill-down** — wireframe with failed-slice inspection (predicate, error, RBAC'd preview). *Captured: Screenshot 2026-07-12 160542.* (slicing-design.md)
20. ⬜ **Event ledger flow** — API enforcement point → ledger (audit + operational classes) → filters/timeline → forwarders (syslog/webhook/file-drop) with the gap detector. (events.md)
21. ⬜ **Security architecture** — trust boundaries: mTLS pinning, envelope encryption, RBAC surfaces, license validation — drawn during the security-architecture design pass; the diagram is part of that spec's definition of done. (security-architecture.md, planned)

## Tables, Sizing, Filesystem (added 2026-07-14)

22. ⬜ **Tables view** — fleet-wide table grid wireframe: identity/physical columns with the "varies" expansion, the status model column with all six states (INCONCLUSIVE called out), sparkline column, filters. (tables.md §2)
23. ⬜ **Table detail page** — wireframe pair: the columns grid (definition type / key badges / actual-in-source / actual-in-target — the type-mapping table as UI) and the history tabs. (tables.md §3)
24. ⬜ **Identity-rename alias window** — timeline diagram: rename point, pre-rename frames in flight resolving via the alias, drain completion, automatic alias retirement event. The mechanism is temporal; prose undersells it. (tables.md §3)
25. ⬜ **Sizing model flow** — inputs (schema, change rates, outage windows, thread counts) → formulas → outputs (tier, quota + thresholds, capture/apply sizing, repository, IOPS); doubles as Replication_Scope's outputs-panel design. (sizing.md §6; HUB-SIZING.md)
26. ✅ **Filesystem trees** — the install/ and state/ trees with backup-class markings, rendered in-document as the layout contract. *Lives in filesystem-layout.md §2–3; exports generated from the doc.* (filesystem-layout.md)

---

**Working rule:** when a concept document changes in a way that alters its diagram, the diagram update is part of the change, not a follow-up. The TOP-07 pattern (documentation screenshots generated by the test suite) extends here: wireframe-class diagrams (12, 18, 19) become Playwright captures of the real UI once it exists, so the pictures cannot drift from the product.
