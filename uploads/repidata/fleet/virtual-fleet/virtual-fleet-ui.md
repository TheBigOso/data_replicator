# Virtual Fleet Console — UI Design

**Project:** Enterprise CDC Replication Platform
**Document type:** UI design specification
**Status:** v1 design — prototyped in `Replicator UI.dc.html`, wireflow in `Virtual Fleet Wireflow.dc.html`
**Related:** `fleet-ui.md` (the level above), `fleet-hierarchy.md` (hierarchy + admin model), `activation-ui.md`, `compare-ui.md`, `run-history.md`, `timeline.md`, `alerts-ui.md`, `jobs.md`, `naming.md`

---

## 1. Purpose

The Virtual Fleet console is level three of the four-level hierarchy (Global Fleet → Fleet → **Virtual Fleet** → Stream).

A **Virtual Fleet** is a logical hub inside one fleet: its own repository namespace, with its own streams, connections, jobs, users, alert rules, and log. Several virtual fleets share one hub server but share nothing else — a frozen VF does not affect its siblings, and a grant on one grants nothing on another.

**This is the working context.** Everything downstream — stream dashboards, connection detail, tables, jobs, events — inherits the current VF. Selecting a VF is what makes the rest of the console concrete.

The page answers four questions in order:

1. **What is this VF and what can I do here?** — the header and its six actions.
2. **Is it healthy?** — the four KPI tiles.
3. **What is inside it?** — the stream table.
4. **What has been happening?** — the VF log, the compare/refresh history, and the VF timeline.

## 2. Access

Four grant tiers, four different surfaces. The console renders the tier the user actually holds; **actions the user cannot perform are absent, not disabled.**

| Grant | Sees | Can do |
|---|---|---|
| **HubOwner** on this VF | Everything | All six header actions, including ⚙ VF Admin |
| **ReadExec** | Everything | Run compares, start/stop/suspend jobs. No create, no delete, no admin |
| **ReadOnly** | Everything | Read only — VF log, Compare history, VF timeline. The four mutating buttons are absent |
| **Fleet / SysAdmin / SuperAdmin** | Everything | Inherited HubOwner |

### 2.1 Entry points

| From | Action |
|---|---|
| Fleet page | `Switch` on a VF row |
| Sidebar tree | `Virtual Fleet · <name>` node |
| Header selector | The VF dropdown, top right |
| Triage or timeline | Deep link, with fleet and VF context switched in |

## 3. Layout — top to bottom

### 3.1 Header

`Virtual fleet · rk-prod` with a sub-line (`N streams · last refresh 6s ago`) and six actions:

**New stream** (primary) · **Activate replication…** · **▤ VF log** · **Compare ▾** · **VF timeline** · **⚙ VF Admin**

### 3.2 KPI row

Four tiles, not six — a VF has no fleet count or org-wide roll-up to report.

| KPI | Value | Red when |
|---|---|---|
| Streams | count in this VF | never |
| P95 latency | worst stream latency | > 60 s |
| Rows/min | sum across streams | never |
| Attention | open concern count | > 0 |

These are the same numbers the fleet timeline shows for this VF one level up. They must agree.

### 3.3 Stream table

| Column | Content |
|---|---|
| Stream | `<source> → <target>`, opens the stream dashboard |
| Hub | the VF id (mono) |
| Status | Healthy · Lagging · Error · Suspended |
| Latency | end-to-end P95, `—` when errored or suspended |
| Rows/min | current throughput |

**Status is derived, not asserted.** It is computed from the capture and apply job states, so a stopped capture reads Error even while apply sits idle-healthy.

**Suspended is not an error.** A paused stream reports Suspended (grey), zero rows, and no latency. It is a deliberate state and never sorts into triage or the Attention count.

### 3.4 Compare and Refresh history

Two panels side by side, every stream in the VF, newest first. One row builder serves both panels *and* the per-stream tabs, so states, attribution, and durations are identical wherever they appear.

- **States:** CURRENT (running now) · DONE/IDENTICAL · DONE/DIFFERENT · DONE/INCONCLUSIVE · CANCELED · FAILED.
- **Attribution:** every row names a person or `scheduler`.
- Each row opens its full record in Events.

## 4. Header actions

### 4.1 New stream

A four-step wizard, each step validated as typed. It **creates a definition, not a running stream** — nothing moves until Activate replication is applied.

| Step | Contents |
|---|---|
| 1 · Identity | Name (identity rules, unique within the VF), description, environment accent |
| 2 · Source & target | Picked from this VF's connections; the picker excludes classes the capability matrix says cannot serve that role. A connection can be created inline without leaving the wizard |
| 3 · Tables | Browse or pattern-match the source catalog; per-table overrides are deferred to the Tables page |
| 4 · Mode | Continuous CDC · scheduled refresh · CDC + scheduled compare; apply style (replica / soft delete / history) and cadence |

**Exit:** the stream appears in the table as **Suspended · not activated**, a tree node is added, and the console offers **Activate replication →** as the obvious next step. The equivalent CLI is shown and exportable.

### 4.2 Activate replication

Plan → review → apply, the pattern operators know from Terraform. The hub diffs the definition against the actual state of every connection and shows exactly what it will create. **Nothing is applied until the plan is approved.** Re-activation is idempotent: unchanged components verify fast and report "no change".

**Component checklist:** jobs · table registration (add or replace) · supplemental logging · state tables · capture position.

**Capture start options:** now · oldest open transaction · rewind N minutes · **recovery — the target's integrate sequence** (the hub-failover path) · custom position.

**Emit time** is set independently of capture start, so you can capture early to catch open transactions while only emitting changes committed from a chosen moment.

**Guard rails:**

- Recreating state tables drops recovery positions — called out in red before apply.
- Recovery rewind is blocked until the integrate sequence has been fetched.
- A partial table selection must include at least one table.
- A custom rewind position must be non-empty; a rewind interval must be positive.

**Chained refresh.** Activation optionally runs the initial load *as-of* the recorded capture position, so the bulk load and CDC meet exactly — no gap, no duplicates.

**Every apply is a record.** Steps, timings, and warnings land in the VF log and the event ledger; the plan is archived as a versioned, attributed artifact.

### 4.3 VF log

Level two of the four-level log hierarchy: `<stream>.out` → **`<vf>.vf.out`** → `<fleet>.fleet.out` → `global.out`.

Every stream in this virtual fleet appends here, merged by time. Opens as a tab in the shared log surface — docks in the page or floats as an overlay alongside stream-level and fleet-level tabs.

- **Line prefix is the job** — `<stream>-cap-<conn>` / `<stream>-integ-<conn>` — so a merged tail stays greppable.
- **Five filters:** Capture · Integrate · Latency · Errors · Events. Filter state is per tab.
- **Follow / Pause** freezes the tail without losing position.
- **Copy** and **Download** emit the filtered view, not the raw buffer.
- Activation and compare milestones interleave as Events lines — one timeline, not two.

### 4.4 Compare

A split button: **Compare history** reads, **New compare** writes.

The compare window is a setup → running → results flow that survives being closed: a running compare continues in the background with a notice chip and a Jobs entry, and reopening restores the window.

| Stage | Contents |
|---|---|
| Scope | Which stream, which tables (all by default), optional row restriction |
| Method | Tiered — row count → checksum → composed → row-by-row. The cheapest method that can answer the question runs first |
| Online truth | Compare a live pair without stopping it; in-flight rows are held and re-checked rather than reported as differences |
| Report | Per-table missing / extra / updated counts |
| Repair | Optional directed repair (insert / delete / update; source→target or reverse), with a WHERE restriction |

**Three honest outcomes:** IDENTICAL · DIFFERENT (with counts) · **INCONCLUSIVE** when rows were in motion. The console never reports a false green.

### 4.5 VF timeline

The operational view the fleet timeline links into. Three bands:

| Band | Contents |
|---|---|
| **CONCERNS** | Open conditions: stream errors, latency over SLA, agent CPU/memory/IO above threshold. Each chip deep-links to the offending object |
| **JOBS** | Capture, apply, refresh, and compare jobs with live state (RUNNING / WAITING / RETRY / DONE / FAILED) and suspend/resume where granted |
| **CHECKS** | System cards for the hub, repo database, and every source/target agent: health, CPU, memory, IO, version |

Ordering is deterministic and thresholds evaluate against **wobble-free values**, so nothing reshuffles or flickers on a live tick. The counts here are exactly the counts the fleet timeline shows for this VF.

### 4.6 VF Admin

The bottom tier of the three-level admin model (Global Admin → Fleet Admin → **VF Admin**). Same admin screen, scoped to one VF:

> VF Admins can edit this virtual fleet's admins, manage/update this virtual fleet, and edit any connection, table, alert, job, and event — within it.

| Tab | Contents | Boundary |
|---|---|---|
| **Virtual fleet** | Description, scheduler cycle, freeze / unfreeze, snapshot, export definition, delete (typed confirmation), stats retention | Freeze suspends the scheduler and **holds capture positions** — it never drops state. Delete additionally requires the fleet-level role |
| **Users** | Accounts whose grants land in this VF, service accounts flagged | Creating an account is Fleet or Global Admin's job — here you attach existing ones |
| **Permissions** | Grants scoped to this VF: HubOwner / ReadExec / ReadOnly | **Cannot grant fleet or repository scope** — a VF admin can never widen their own reach |
| **Alert rules** | Rules watching this VF's logs, one notification stream each, with the retry/backoff curve and delivery-failure history | Rules cannot reach outside the VF |

**Gate:** ⚙ renders for HubOwner on this VF, or anyone with an inherited fleet/repository grant.

## 5. The lifecycle this page owns

```
New stream → Suspended · not activated → Activate (plan) → Apply + chained refresh
   → Healthy · capturing → Compare (prove it) → Deactivate / retire
```

Each transition writes to the VF log and the event ledger with an attributed, versioned artifact. Re-activation after a definition change re-enters at **plan**, never at create — there is no second path that skips the diff.

## 6. Rules this page holds to

1. Nothing replicates until a plan is applied — creation is always inert.
2. A compare never reports a false green; rows in motion are INCONCLUSIVE.
3. Freeze holds positions; only an explicit teardown drops state.
4. A VF admin cannot widen their own scope.
5. Suspended is a deliberate state and never enters triage.
6. Every action shows its equivalent CLI and is exportable.
7. Stream status is derived from job state, never asserted.
8. KPI and timeline counts agree with the fleet level above.

## 7. Acceptance criteria

| ID | Criterion |
|---|---|
| VFC-1 | The console renders per grant tier; ReadOnly and ReadExec never see mutating actions as disabled controls |
| VFC-2 | Four KPI tiles compute over this VF only, and their values match the fleet timeline's figures for the same VF |
| VFC-3 | Stream status is derived from capture and apply job state; a stopped capture reads Error regardless of apply state |
| VFC-4 | Suspended streams report zero rows and no latency, and are excluded from Attention and triage |
| VFC-5 | The New stream wizard validates identity, source/target eligibility, table selection, and mode; the resulting stream is inert until activated |
| VFC-6 | Activation shows a computed plan before any change is applied; re-activation of an unchanged definition reports no change |
| VFC-7 | All five capture-start options behave as specified; recovery rewind is blocked until the integrate sequence is fetched; state-table recreation is warned in red |
| VFC-8 | Chained refresh loads as-of the recorded capture position, verified by a clean compare with zero duplicates |
| VFC-9 | The VF log tails `<vf>.vf.out` with every stream merged by time, job-prefixed, filterable by the five standard filters, and openable in the overlay |
| VFC-10 | Copy and Download emit the filtered view, not the raw buffer |
| VFC-11 | A running compare survives closing its window, continues in the background with a Jobs entry, and restores on reopen |
| VFC-12 | Compare reports IDENTICAL, DIFFERENT with counts, or INCONCLUSIVE when rows were in motion — never a false green |
| VFC-13 | The VF timeline's CONCERNS, JOBS, and CHECKS bands order deterministically against wobble-free values |
| VFC-14 | VF Admin's Permissions tab cannot grant fleet or repository scope |
| VFC-15 | Freeze suspends the scheduler and holds capture positions; no state is dropped without an explicit teardown |
| VFC-16 | Every lifecycle transition writes an attributed, versioned record to the VF log and the event ledger |
