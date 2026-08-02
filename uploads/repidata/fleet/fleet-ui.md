# Fleet Console — UI Design

**Project:** Enterprise CDC Replication Platform
**Document type:** UI design specification
**Status:** v1 design — prototyped in `Replicator UI.dc.html`, wireflow in `Fleet Wireflow.dc.html`
**Related:** `fleet-hierarchy.md` (hierarchy + admin model), `global-fleet-ui.md` (the level above), `users-permissions-ui.md` (admin tabs), `timeline.md` (fleet timeline), `alerts-ui.md`, `naming.md`

---

## 1. Purpose

The Fleet console is level two of the four-level hierarchy (Global Fleet → **Fleet** → Virtual Fleet → Orca). A **Fleet** is one enrolled hub server; the virtual fleets inside it are the working contexts where replication actually runs.

This is the **first screen where an operator can change things**. The Global Fleet console above it grants sight, not touch; the Fleet console is where a fleet admin creates virtual fleets, manages the people who can reach them, and reads the merged log of everything the hub server is doing.

The page answers three questions in order:

1. **What is this fleet, and am I allowed to act on it?** — the header.
2. **What is inside it, and where do I go?** — the virtual-fleet table.
3. **What is happening right now, and what is wrong?** — the fleet log and the fleet timeline.

## 2. Access

Any grant that reaches the fleet opens the page: a grant on the fleet itself (`streamsrv-*`) or on any virtual fleet inside it. **HubOwner at fleet scope is the Fleet Admin role.** SuperAdmin and SysAdmin reach every fleet.

A user with no grant reaching the fleet never sees it — it is absent from the sidebar tree and from the global fleet matrix, not greyed out.

**Read versus write.** ReadOnly and ReadExec grants render the whole page, but the two mutating header actions (⚙ Fleet Admin, New virtual fleet) are **not rendered at all**. The Fleet log button stays — it is a read surface. The console never shows a disabled button the user cannot enable.

### 2.1 Entry points

| From | Action |
|---|---|
| Global Fleet console | `Open fleet →` on a fleet row |
| Sidebar tree | `Fleet · <name>` node |
| Sign-in | Landing screen when the user's strongest grant is fleet-scoped |
| Triage row | Deep link from Global Fleet, with fleet context switched in |

## 3. Layout — top to bottom

### 3.1 Fleet header

One line of identity, one line of address, three actions.

- **Display name** — `Fleet · TITAN_1`, with an inline ✎ rename control.
- **State pill** — Connected / Enrolling / Unreachable.
- **★ in sidebar** — pin toggle; a pinned fleet stays in the tree regardless of navigation.
- **Sub-line** — organization label and the hub URL in mono (`orca-east.corp.example:8443`).
- **Actions** — ▤ Fleet log · ⚙ Fleet Admin · **New virtual fleet** (primary).

**The display name is an alias.** Renaming is cosmetic. The enrollment id is what grants, scopes, log file names, event records, and the API use, and it never changes. This rule is load-bearing: a fleet renamed to `TITAN_1` still writes `streamsrv-corp.fleet.out` and still matches grants scoped to `streamsrv-corp`.

### 3.2 Virtual fleet table

Every VF in the fleet, including ones reachable only through a SuperAdmin grant.

| Column | Content |
|---|---|
| Virtual fleet | State dot + name (mono), links into that VF |
| State | Live / Errors / Frozen |
| Orcas | Count of orcas defined in that VF |
| Connections | Distinct capture + apply endpoints |
| Users | Accounts with a grant reaching the VF |
| P95 latency | Worst orca latency, `—` when errored, `frozen` when suspended |
| Your access | Strongest grant held on that VF, plus a **Switch** button |

**The access column is the honest one.** It names the strongest grant the current user holds on that VF; grants inherited from the fleet show as the fleet role rather than "none". VFs the user cannot reach at all are absent from the table, not greyed.

**Switch** makes that VF the working context — the header selector, the sidebar tree, and every downstream screen follow in one motion. The current VF has no Switch button.

### 3.3 Fleet log

Level three of the four-level log hierarchy: `<orca>.out` → `<vf>.vf.out` → **`<fleet>.fleet.out`** → `global.out`.

Every orca in every virtual fleet of this fleet appends here, merged by time. It opens as a tab in the shared log surface, so it docks in the page or floats as an overlay alongside orca-level and VF-level tabs.

- **Line prefix carries the VF.** Each line is namespaced `<vf>/<job>:` so a merged tail stays readable and greppable.
- **Five filters**, the same at every level: Capture · Integrate · Latency · Errors · Events. Filter state is per tab, not global.
- **Follow / Pause** freezes the tail without losing scroll position.
- **Copy** and **Download** take the filtered view, not the raw buffer.
- **File name is the receipt** — `<fleet-id>.fleet.out` uses the enrollment id, never the display alias.

### 3.4 Fleet timeline

The same triage-first split as the global fleet matrix, one tier down.

- **NEEDS TRIAGE · N** — VFs with open concerns, red left edge, sorted worst-first.
- **RUNNING NORMALLY · N** — everything else.

Each VF card carries counts (CONCERNS · JOBS · CHECKS), condition chips, and a `VF timeline →` link. Every chip deep-links to the offending connection or orca with context switched in.

## 4. Header actions

### 4.1 ▤ Fleet log

Opens (or focuses) the fleet-log tab. Available to every role that can open the page.

### 4.2 ⚙ Fleet Admin

The middle tier of the three-level admin model (Global Admin → **Fleet Admin** → VF Admin). Same admin screen, scoped down:

> Fleet Admins can edit fleet admins, manage/update/create virtual fleets in this fleet, and edit any connection, table, alert, job, and event — within this fleet.

| Tab | Contents | Boundary |
|---|---|---|
| **Users** | Accounts whose grants land in this fleet. Create, disable, reset auth; service accounts flagged separately. | Cannot create accounts scoped outside the fleet — that is Global Admin |
| **Permissions** | The grant table filtered to this fleet and its VFs. Grant HubOwner / ReadExec / ReadOnly at fleet or VF scope. | **FleetViewer and SysAdmin are not grantable here** — repository scope belongs to Global Admin |
| **Virtual fleets** | Per-VF row actions: freeze / unfreeze the scheduler, snapshot, export definition, delete (typed confirmation), stats-retention tuning. | Freeze holds capture positions; it never drops state |
| **Fleet settings** | Display alias, sidebar pin default, alert-manager cycle, retention windows. | Enrollment id and hub URL are read-only — changing those is a re-enrollment, done from Global Admin |

**Gate:** the ⚙ button renders only for HubOwner-at-fleet-scope, SysAdmin, or SuperAdmin.

### 4.3 New virtual fleet

A virtual fleet is its own repository namespace on the same hub server: its own orcas, connections, jobs, users, and log. Creating one is cheap and reversible; it starts empty and inert.

**Modal fields:** Name (required) · Description. A note states the owning fleet, that the creator becomes the first VF Admin, and that nothing replicates until a connection and an orca are added.

**Validation:** the name follows the platform identity rules and must be unique across the whole hub server, refused as typed.

**On create:** the VF appears in the table as Live · 0 orcas, is added to the sidebar tree, an ENROLL-class event lands in the fleet log, and the modal closes into the new VF's empty state.

## 5. Sibling pages — what belongs where

| Level | Scope | What it can do |
|---|---|---|
| Global Fleet | Every enrolled fleet | Read-only across systems; triage and navigation only |
| **Fleet** | One hub server | VF inventory, merged log, fleet-wide triage, fleet admin |
| Virtual Fleet | One logical hub | The working context: orcas, connections, jobs, events, VF log and timeline |
| Orca / Connection | One replication unit or endpoint | Tables, capture/integrate, compare, refresh, server health |

## 6. Rules this page holds to

1. Display aliases never leak into ids, log file names, scopes, or events.
2. Actions the user cannot perform are absent, not disabled.
3. Triage ordering is deterministic — rows never reshuffle on a live metric tick.
4. Every count on the page derives from visible VFs only.
5. Switching VF changes context everywhere at once: header, tree, and all downstream screens.

## 7. Acceptance criteria

| ID | Criterion |
|---|---|
| FLC-1 | The page opens for any grant reaching the fleet; fleets with no reaching grant are absent from the tree and the global matrix |
| FLC-2 | ⚙ Fleet Admin and New virtual fleet render only for HubOwner-at-fleet-scope, SysAdmin, or SuperAdmin; never as disabled controls |
| FLC-3 | Renaming a fleet changes the displayed label only — enrollment id, grant scopes, log file names, and event records are unaffected |
| FLC-4 | The VF table lists every VF in the fleet with orca, connection, user, and P95 figures; the access column names the strongest held grant, including grants inherited from the fleet |
| FLC-5 | Switch sets the working context across header, tree, and all downstream screens in one action; the current VF has no Switch |
| FLC-6 | The fleet log tails `<fleet-id>.fleet.out` with every VF's orcas merged by time, each line prefixed `<vf>/<job>`, filterable by the five standard filters, and openable in the floating overlay |
| FLC-7 | Copy and Download emit the filtered view, not the raw buffer |
| FLC-8 | The fleet timeline splits VFs triage-first with deterministic ordering; every condition chip deep-links to the offending connection or orca |
| FLC-9 | Fleet Admin's Permissions tab cannot grant repository-scope permissions (FleetViewer, SysAdmin) |
| FLC-10 | Creating a virtual fleet validates name uniqueness across the hub server, adds the VF to the table and tree, writes an ENROLL event to the fleet log, and lands the user in the new VF's empty state |
