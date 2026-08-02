# Global Fleet Console — UI Design

**Project:** Enterprise CDC Replication Platform
**Document type:** UI design specification
**Status:** v1 design — prototyped in `Replicator UI.dc.html`, wireflow in `Global Fleet Wireflow.dc.html`
**Related:** `fleet-hierarchy.md` (hierarchy + admin model), `timeline.md` (fleet timeline), `alerts-ui.md` (triage sources), `naming.md`

---

## 1. Purpose

The Global Fleet console is the top of the four-level hierarchy (Global Fleet → Fleet → Virtual Fleet → Stream): one screen that pulls every enrolled fleet (hub server) into a single view so a super admin or executive can monitor anything affecting any system without switching contexts. HVR never had a cross-hub-server view; this console is the reason the level exists.

It is **read-only across systems** — it grants sight, not touch. Operating on anything means switching into that fleet, which becomes the working context.

## 2. Access — FleetViewer

- Opening the console requires the repository-level **FleetViewer** permission. Without it, the screen shows a locked card explaining the permission and where to ask (Admin → Permissions).
- Even with FleetViewer, **visibility follows grants**: fleets where the user holds no grant stay hidden entirely. A user with grants on zero systems sees the empty state ("visibility follows grants — ask a fleet's admin").
- Header actions: **⚙ Global Admin** (SuperAdmin surface) and **New fleet** (enroll a system).

## 3. Layout — top to bottom

Ordered by the Overview → Attention Areas → Action Zone layering: the screen answers "is anything wrong?" before it lists anything.

### 3.1 KPI hero row (Overview)

Six tiles, org-wide, computed over visible fleets only:

| KPI | Value | Sub-line | Red when |
|---|---|---|---|
| Fleets | visible count | `N enrolled` | never |
| Virtual fleets | total VFs | `N with errors` / `all reachable` | any VF in Errors |
| Streams | `running / total` | — | never |
| Worst P95 | worst stream latency | that stream's id | > 60 s |
| Rows/min | org-wide sum | `org-wide` | never |
| Attention | triage-item count | `needs triage` | > 0 |

### 3.2 Needs-triage strip (Attention Areas)

Everything hot in the organization, one row per issue, sorted worst-first with a deterministic tiebreak (rank, then breadcrumb+title) so live metric wobble never reorders rows. Fixed column widths so rows never jump: severity pill (64px) · breadcrumb `fleet / vf / object` (250px, mono) · issue title (265px, tabular numerals) · detail (flex) · **date + time raised and relative age** (150px, e.g. `Jul 31 · 09:14 · 22m ago`) · `open →`.

Sources: stream errors, high stream latency, CPU/memory/IO concerns on any agent or hub (thresholds CPU/mem > 80 %, IO > 320 MB/s — checked against wobble-free values), delivery-failure alerts. **Every row is a deep link**: clicking lands on the exact problem (the stream, the connection's Server health panel, the alert) with the fleet/VF context switched in.

The strip renders only when there is something to triage; a clean org goes straight from KPIs to the fleet list.

### 3.3 Fleet health matrix (Action Zone)

Search (fleets, divisions, virtual fleets) + state filter (All / Errors / Frozen / Live) + shown-count.

One expandable row per fleet, triage-first ordering (fleets with concerns sort to the top and take a red left edge; healthy fleets keep the environment accent):

- **Collapsed row:** caret · FLEET badge · state dot · name · org · state pill · counts line (`N VFs · running/total streams · worst P95 · rows/min`) · `⚠ N concerns` badge when hot · hub URL (mono) · pin-to-sidebar toggle · **Open fleet →**.
- **Expanded:** a VF table — Virtual fleet · State · Streams · Connections · Users · P95 latency · Your access — each row enterable; a **Switch** button appears where access allows, making that VF the working context.

### 3.4 Org-wide facts

Small facts grid: virtual fleets connected, agents enrolled (with version stragglers), users active, events in 24 h, license model.

### 3.5 Global log

`global.out` — the top of the four-level log hierarchy (`<stream>.out` → `<vf>.vf.out` → `<fleet>.fleet.out` → `global.out`). Every fleet in the organization appends here, merged by time. Docked 240 px dark panel at the bottom of the console: filter chips, follow mode, and **⇱ Overlay** to reopen it in the floating log viewer alongside any other tabs.

## 4. Interactions

- **Pin** on a fleet row keeps that fleet in the sidebar tree regardless of navigation.
- **Open fleet →** switches into the Fleet view (its VF list, fleet log, fleet timeline).
- Triage-row click = deep link (see 3.2).
- Search and filter compose; the shown-count reflects both.

## 5. Acceptance criteria

| ID | Criterion |
|---|---|
| GFC-1 | Console is gated by FleetViewer; without it a locked explainer renders; with it, only granted fleets appear (empty state otherwise) |
| GFC-2 | Six KPI tiles compute over visible fleets; Attention, Worst P95 > 60 s, and VF-error counts render in danger red |
| GFC-3 | Triage strip rows carry severity, breadcrumb, title, detail, and raised date+time with relative age, in fixed-width columns that never reflow on live ticks |
| GFC-4 | Triage ordering is deterministic (rank, then name) — live metric wobble never reorders or re-admits rows |
| GFC-5 | Every triage row deep-links to the exact problem surface with fleet/VF context switched |
| GFC-6 | Fleet rows sort triage-first with red left edge and ⚠ concern badge; expanded rows list VFs with per-VF stats and access; Switch appears only where granted |
| GFC-7 | Search + state filter compose; shown-count updates; pins persist per user |
| GFC-8 | Global log tails global.out (all fleets merged, time-ordered), filterable, and opens in the floating overlay viewer |
| GFC-9 | Console is read-only across systems — every mutating action requires switching into the owning fleet/VF first |
