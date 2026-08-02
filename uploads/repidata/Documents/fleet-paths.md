# Fleet Paths — the console tree on disk

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design; the path model
**Related:** `filesystem-layout.md` (the install/state contract and backup classes), `architecture.md` §2.2 (the console hierarchy), `fleet-hierarchy.md`, `stream.md`, `connection.md`, `events.md`

---

## 1. Purpose

`filesystem-layout.md` enumerates *which directories exist* on a fleet. This document defines *how the hierarchy nests inside them* — the rule that turns a place in the console into a path on disk.

**One addressing scheme.** Where an operator navigates to a thing, that is where the thing's files live. An engineer given a screen and an engineer given a shell should arrive at the same directory without translation.

```
Console                                                    Disk
Fleet · TITAN_1 › Virtual Fleet · orca-east › SNOWFLAKE-PRD
  →  state/vf/orca-east/connections/SNOWFLAKE-PRD/
```

## 2. The first rule: two levels have no disk

The navigation tree has four levels; **only the bottom two are storage.**

| Console level | On disk | Why |
|---|---|---|
| **Global Fleet** | **Nothing, anywhere** | A cross-fleet *view*. It owns no host, so it owns no bytes — it is a query fanned out over every enrolled fleet |
| **Global Admin** | **Nothing** | Accounts, grants, and enrollment records are repository rows |
| **Fleet** | **The state root itself** | A fleet *is* a hub server. The fleet is not a directory inside the tree; it is the tree |
| **Virtual Fleet** | `vf/<vf-id>/` | The first physical segment |
| Everything below | Subdirectories of the VF | See §4 |

This is the honest consequence of hub-routed architecture: **there is no machine on which the Global Fleet exists.** Anything the Global Fleet console shows is assembled at read time from the fleets it can reach, which is why it is read-only across systems and why losing one hub degrades that view rather than corrupting it.

It also means the fleet segment is implicit. `state/vf/orca-east/…` is unambiguous *because* the state root belongs to exactly one hub server. Exports and snapshots re-attach the fleet id at their boundary (§7).

## 3. The second rule: paths use enrollment ids, never display names

The console shows `Fleet · TITAN_1`. Disk says `streamsrv-corp`.

Display names are **aliases** — renaming a fleet or VF is a cosmetic, reversible metadata change (`fleet-ui.md` §3.1). If a rename moved directories it would invalidate every open file handle, every capture checkpoint path, and every archived log reference, turning a label edit into an outage.

**Therefore:**

1. Every path segment is an **enrollment id**, fixed at creation and immutable for the object's life.
2. Ids obey the platform identity rules: lowercase `a–z 0–9 . _ -`, no leading dot, unique within their parent scope. This is also what makes them safe on every filesystem the product supports, including case-insensitive ones.
3. A rename writes a `DEFINITION CHANGE` event and changes nothing on disk.
4. No path anywhere contains a user-chosen display string — not in directory names, not in file names, not in archive names.

## 4. The Virtual Fleet subtree

```
state/                                    ← the Fleet (this hub server)
├─ <fleet-id>.fleet.out                   fleet log: every VF below, merged by time
│
└─ vf/
   ├─ orca-east/                          ← Virtual Fleet
   │  ├─ orca-east.vf.out                 VF log: every stream in this VF, merged
   │  │
   │  ├─ connections/
   │  │  ├─ ORA-ERP01/                    ↑ source
   │  │  │  ├─ agent.out                  agent-side log, shipped and retained here
   │  │  │  ├─ probe.out                  reachability / heartbeat probe history
   │  │  │  └─ tests/                     connectivity-test results, newest last
   │  │  ├─ PG-BILLING/
   │  │  ├─ DB2-MFG/
   │  │  ├─ SNOWFLAKE-PRD/                ↓ target
   │  │  ├─ PG-ANALYTICS/
   │  │  └─ DATABRICKS-LH/
   │  │
   │  ├─ streams/
   │  │  ├─ erp-financials/
   │  │  │  ├─ erp-financials.out         the stream log
   │  │  │  ├─ filelog/                   change files, <sequence> per the published format
   │  │  │  ├─ checkpoints/               capture position + retained recovery checkpoints
   │  │  │  ├─ enrollment/                per-table registration snapshots
   │  │  │  └─ jobs/                      <job-id>.out run logs for this stream's jobs
   │  │  ├─ billing-invoices/
   │  │  └─ mfg-workorders/
   │  │
   │  ├─ reports/                         compare / sync report artifacts
   │  ├─ plans/                           applied activation plans, versioned
   │  └─ intermediate/                    ◻ compare + refresh working files
   │
   ├─ orca-west/
   └─ orca-euc/
```

### 4.1 Not every node in the tree is a directory

The console shows six things under a Virtual Fleet. Only two of them are storage:

| VF child | On disk | Where the data actually lives |
|---|---|---|
| **Connections** | ✔ `connections/<id>/` | Logs and probe history here; *configuration* and credentials are repository rows (credentials envelope-encrypted, never on agent disk — `connection.md` §5) |
| **Streams** | ✔ `streams/<id>/` | The only branch that descends further, matching the navigation tree |
| **Jobs** | ✘ | A job is a scheduler record in the repository. Its **run log** is a file, filed under the stream that owns it: `streams/<stream>/jobs/<job-id>.out` |
| **Events** | ✘ | The ledger is repository rows. Only its **artifacts** are files (`reports/`, `plans/`), and only the file-drop forwarder stages copies (`events-forward/`) |
| **VF Timeline** | ✘ | Rendered from repository metrics series; nothing is stored per-timeline |
| **Fleet Alerts** | ✘ | Rules and delivery attempts are repository rows; the alert manager's own cycle log is a run log |

**The rule:** *bytes that flow* live on disk; *facts about them* live in the repository. Change files, logs, and artifacts are the first kind. Definitions, grants, job state, events, and metrics are the second.

This is what keeps the repository small enough to restore from a plain `pg_dump` (`architecture.md` §3.2) — and why a fleet can be imaged for forensics without exposing row data, since everything in `filelog/` is AES-256-GCM ciphertext.

## 5. The log hierarchy is the path hierarchy

The four-level log model (`virtual-fleet-ui.md` §4.3) is not a coincidence — each level's file sits at that level's directory:

| Level | Path | Contents |
|---|---|---|
| Stream | `vf/<vf>/streams/<stream>/<stream>.out` | That stream's capture, apply, and event lines |
| Virtual Fleet | `vf/<vf>/<vf>.vf.out` | Every stream in the VF, merged by time, job-prefixed |
| Fleet | `<fleet-id>.fleet.out` | Every VF in this fleet, merged, `<vf>/<job>`-prefixed |
| **Global** | **— no file —** | Assembled by the Global Fleet console at read time by merging each reachable fleet's `.fleet.out` |

`global.out` is a **name for a view, not a file.** Nothing writes it, because §2: the Global Fleet has no host. The console names it `global.out` so the four levels read consistently, and the download it offers is generated on demand from the fleets the user's grants reach.

**Each level is a strict superset of the one below**, so a line is written once at stream level and *projected* upward — the higher files are materialized views maintained by the hub, not independent copies that could disagree.

## 6. What the path model buys

**Quotas are directory quotas.** The ARC-13 file-store quota is per virtual fleet, which is now a real path: `vf/<vf>/` is the accounting unit. Unacknowledged bytes, oldest unacknowledged age, and forecast-time-to-quota are computed per subtree, so one runaway VF cannot starve its siblings.

**Deletion is a subtree.** Deleting a VF removes `vf/<vf>/` entirely after the guarded teardown; retiring a stream removes `streams/<stream>/` after GC. Nothing is scattered, so nothing is orphaned. Ack-based GC still owns deletion *inside* `filelog/` — the joint low-water mark is never overridden by a delete elsewhere.

**Scope is inspectable.** "Which files does this VF own?" is `du -sh vf/orca-east/`, not a query. Security teams scanning a host can attribute every byte to a console object.

**Restore is per-scope.** A single VF can be restored into a rebuilt fleet by restoring its subtree plus its repository rows, without touching its siblings.

**Isolation is structural, not conventional.** Two virtual fleets in one fleet share a process and a repository but no directory — which is the disk-level statement of the same promise the permission model makes.

## 7. Boundaries: exports, snapshots, archives

Inside a fleet the fleet id is implicit; the moment bytes leave, it must be explicit.

- **VF snapshot / export** — the archive root is `<fleet-id>/<vf-id>/`, so two exports from different fleets never collide when unpacked side by side.
- **Log download** — a downloaded file is named `<fleet-id>.<vf-id>.<stream>.out`; the console's flat display name is not used.
- **Event export** — the manifest carries fleet and VF ids for every record (`events-ui.md` §9.3).
- **File-drop forwarding** — staged under `events-forward/<fleet-id>/`, so an air-gapped sink receiving from several fleets keeps them apart.

## 8. Rules this model holds to

1. The Global Fleet and Global Admin have no disk presence on any host.
2. A fleet's state root *is* the fleet; the fleet is never a path segment inside itself.
3. Every path segment is an immutable enrollment id — display names never reach disk.
4. Renaming changes metadata and an event; it moves nothing.
5. Bytes that flow live on disk; facts about them live in the repository.
6. Streams is the only VF child that descends further, on screen and on disk alike.
7. Each log level is a projection of the one below, not an independent copy.
8. `global.out` is a view name; nothing writes it.
9. Quota, deletion, restore, and attribution are all per-subtree.
10. Any path not documented here or in `filesystem-layout.md` §3 is a bug (FSL-01 sweeps for it).

## 9. Acceptance criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| HPT-01 | Every file a fleet writes resolves to a documented path under the state root, and its console object is derivable from that path alone |
| HPT-02 | No path segment or file name anywhere contains a display alias; renaming a fleet, VF, or stream leaves the filesystem byte-identical and writes one DEFINITION CHANGE event |
| HPT-03 | Jobs, Events, VF Timeline, and Fleet Alerts create no directories of their own; their run logs and artifacts appear under the owning stream or the VF's `reports/` and `plans/` |
| HPT-04 | The stream, VF, and fleet log files exist at their documented paths, each a strict superset of the level below, verified line-for-line after a mixed workload |
| HPT-05 | No fleet writes a `global.out`; the Global Fleet console's download is generated at read time from reachable fleets and is correct under a partial-reachability fixture |
| HPT-06 | File-store quota, unacknowledged bytes, and forecast-to-quota are computed per `vf/<vf-id>/` subtree; a VF at quota does not impede its siblings |
| HPT-07 | Deleting a VF or retiring a stream removes exactly its subtree, leaves no orphans elsewhere, and never overrides `filelog/` acknowledgment-based GC |
| HPT-08 | Exports, snapshots, downloaded logs, and forwarded events all carry explicit fleet and VF ids; two fleets' artifacts unpack side by side without collision |

## 10. Open questions

Whether `connections/<id>/` should retain agent logs for connections shared by several VFs in one fleet (today each VF keeps its own copy under its own subtree — simple and attributable, but duplicative for a busy shared agent) needs a volume number before it is settled. Path length limits on Windows agents need checking against the deepest documented path (`vf/<vf>/streams/<stream>/jobs/<job-id>.out`) plus a customer-chosen state root. Whether per-VF subtrees should be separate mounts in high-isolation deployments — enabling true per-tenant quotas at the filesystem layer — belongs with the containerized-deployment pattern already parked in `filesystem-layout.md` §9.
