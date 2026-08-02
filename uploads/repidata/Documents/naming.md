# Naming — Terminology Decisions

**Project:** Enterprise CDC Replication Platform
**Document type:** Decision record and enforcement plan
**Status:** Recommendations drafted; contested terms await owner sign-off before the rename sweep

---

## 1. The Principle

Three buckets, three rules. **Industry-generic terms** (used across GoldenGate, Qlik, Debezium, DBMS documentation) are free to use — nobody owns "capture" or "hub." **HVR's distinctive coinages** — words HVR invented or made distinctive as product vocabulary — are never adopted, both for legal hygiene and because a competitor wearing HVR's vocabulary reads as a clone. **Our own coinages** name the things we invented (sync report, origin lineage, capability matrix, the plan). The test for bucket two: *would an HVR-certified engineer reading our docs feel at home because the concepts are familiar, or because the words are HVR's?* The first is fine; the second is the problem.

## 2. The Decision Table

### Safe — industry-generic, kept

| Term | Why it's safe |
|---|---|
| hub, agent | Generic architecture vocabulary (GoldenGate hub deployments, agents everywhere) |
| capture | Generic CDC term (SQL Server "capture instance", log capture broadly) |
| source / target, refresh, compare | Plain English, used industry-wide (materialized-view refresh; data validation/compare) |
| state table, checkpoint, supplemental logging | DBMS-native vocabulary (supplemental logging is Oracle's own term) |
| soft delete | Generic data-modeling term |
| agent enrollment | Standard security/PKI vocabulary (device enrollment) — distinct from HVR's *table* enrollment below |
| initial load, spool, staging | Generic operations vocabulary |

### HVR coinages — renamed

| HVR term | Our term | Rationale |
|---|---|---|
| **Channel** | **Stream** | **Owner decision (2026-08-01), superseding the earlier "Pipeline" recommendation.** The console says Stream throughout and the object is a stream of changes, not a static conduit. Industry-neutral, self-explaining. *Rename sweep executed 2026-08-01:* `channel.md` → `stream.md`, CHA-xx → STR-xx, and all cross-references updated. |
| **Location** | **Connection** | **Owner decision (2026-07-14).** Industry-standard (Informatica and others), and more self-explaining than "location" — a connection *to* Oracle prod is exactly what the object is. Location groups → **connection groups**; the auto-created SOURCE/TARGET groups keep their role names. The plain word "location" remains usable in ordinary English (file paths, directories) — the ban is on the object concept. |
| **TimeKey** | **History style** (append-only change history) | TimeKey is pure HVR vocabulary. Our three styles become: **replica**, **soft delete**, **history**. The `_origin` metadata columns are already ours. TimeKey truncate marker → **history truncate marker**. |
| **Burst** (Method=Burst, `__b` tables) | **Batched apply** (stage-and-merge) | We already describe the mechanism as stage-and-merge; name it what it does. Continuous vs batched apply. |
| **Integrate** (as the job/role name) | **Apply** | "Integrate" alone is English, but the Capture/Integrate *pairing* is HVR's signature. Capture job / **apply job**; integrate agent → **apply agent**. Classic replication vocabulary (apply process). |
| **Slicing / slices** | **Segments / segmented load** | Slicing is HVR-distinctive. Segment, segment map, **Segment Advisor**. |
| **Table enrollment** | **Table registration** (the capture registry) | Enrollment stays reserved for agent/PKI usage where it's standard; HVR's table-enrollment coinage goes. |
| **Router (files/directory)** | **File log** | Already renamed throughout — the file log is our published-format transport. |
| **Actions** (the config mechanism) | **Structured settings** | Already renamed throughout; the four-level ladder is ours. |
| **HVR_HOME / HVR_CONFIG** | **install/ and state/** | Already renamed (filesystem-layout.md). |
| **hvr_* column/table prefixes** | Product-prefix TBD with the product name | Placeholder rule: no `hvr` string anywhere, ever — including test fixtures. |

### Decision needed — owner's call

| Term | Options | Recommendation |
|---|---|---|
| **Activate / Deactivate Replication** | keep (generic English) · **deploy/retire** · **provision/decommission** | Keep **activate/deactivate** — plain English, used beyond HVR, and our plan-based framing already differentiates it. Low risk. |
| **Refresh** (as the feature name) | keep · **load** (initial load / reload / repair load) | Keep **refresh** — generic (materialized views), and "repair load" reads worse than "row-wise refresh." Low risk. |
| **Compare** | keep · **validate / validation** | Keep **compare** — generic verb; "sync report" is the branded layer above it and that one is ours. |
| Product name, binary names (`replhub`, `replagent`, `replctl`) | open | Placeholder binaries are ours and safe; final names follow the product-name decision (long-standing open item). |

## 3. Rollout — the sweep, once names lock

Renaming mid-design one term at a time would churn every document repeatedly; instead: **lock this table, then run one dedicated rename sweep** across all specs, the diagram plan, the Lucid diagrams, wireframes, and Replication_Scope's UI strings. The sweep is mechanical because this table is the mapping. Until the sweep, HVR-bucket terms appearing in our documents are *known debt tracked here*, not decisions. Parity-matrix rows quoting HVR's own terms (left column) are exempt forever — naming what we're comparing against is the point of those tables.

The sweep also renames **files and criterion prefixes** in one motion, since the traceability matrix is being reconciled anyway. **Done (2026-08-01):** `channel.md` → `stream.md` (CHA-xx → STR-xx), across every spec and the matrix, with parity-matrix left columns left quoting HVR's "Channel" as the exemption requires. **Also done (2026-08-01):** `location.md` + `connections.md` merged into `connection.md` (LOC-xx ids retained for traceability). **Still outstanding:** `slicing-design.md` → `segments.md` (SLC-xx → SEG-xx). Doing IDs and prose together means the matrix is rebuilt once against the final vocabulary rather than twice.

## 4. Enforcement

**NAM-01 — banned-terms lint.** A CI check over the documentation set, UI string catalog, API surface (OpenAPI), CLI help text, and schema identifiers, failing on any occurrence of the banned list (stream, location-as-the-object-concept, TimeKey, burst-as-mode-name, slicing/slice, table enrollment, router-file vocabulary, any `hvr` string) outside parity-matrix left columns and explicitly quoted HVR material. The same trick as the events completeness sweep: the rule is a build failure, not a style guide.

**Test plan:** one phase — implement the lint against this table's banned list, run it, burn down the hits from the rename sweep, then keep it green forever. **Acceptance:** | NAM-01 | The banned-terms lint runs in CI over docs, UI strings, API, CLI, and schema identifiers, and passes with zero occurrences outside quoted-HVR contexts |

## 5. Open Questions

The product name unlocks the prefix rule, the binary names, and the metadata-column prefix — it remains the oldest open item on the board. ~~Whether "hub" should eventually carry a product-flavored name (fleet? control plane?) is a branding question~~ **Resolved (2026-07): the fleet vocabulary is adopted** — see `fleet-hierarchy.md`. A hub server is a **Fleet**; a logical hub on it is a **Virtual Fleet**; the cross-company view is the **Global Fleet** console. "Hub" remains acceptable in low-level/transport contexts (hub-routed, hub repository) but user-facing hierarchy language uses Fleet / Virtual Fleet. The rename sweep should carry this mapping. Marketing may want distinct names for the sync report and the origin lineage as headline features; those are ours to brand freely.
