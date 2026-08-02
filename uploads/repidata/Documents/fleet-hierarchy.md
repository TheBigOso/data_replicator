# Fleet Hierarchy & Admin Model — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and decision record
**Status:** v1 design — prototyped in `Replicator UI.dc.html`

## 1. Why this exists

HVR's hub model has a structural gap we lived with for ten years: a company runs multiple hub servers, each hub server hosts multiple hubs, and **there is no single place to see all of them**. Every hub server is its own island with its own login, its own UI, its own alert surface. In a large corporation — one division building rockets, another building radar — each division runs its own hub server, and each division further splits work into isolated environments. Nobody, not even the platform owner, can answer "what is the state of replication across the company" without opening N browser tabs.

This platform fixes that with an explicit four-level hierarchy and a Global Fleet console that spans all of it.

## 2. The hierarchy

```
Global Fleet Manager        — overview of all fleets (all hub servers)
└── Global Fleet Admin
└── Fleet                   — one hub server; overview of its virtual fleets
    └── Fleet Admin
    └── Virtual Fleet       — isolated environment; overview of its streams
        └── Virtual Fleet Admin
        └── Stream
            ├── Connections
            ├── Tables
            ├── Monitoring
            ├── Jobs
            ├── Events
            └── Admin
```

| Level | Maps to | Contains | Isolation boundary |
|---|---|---|---|
| **Global Fleet** | The whole company | All fleets | Visibility gated by `FleetViewer` |
| **Fleet** | One hub server (per department/division) | Virtual fleets | Own users, own repository |
| **Virtual Fleet** | One logical hub on that server (per environment/project: prod, pre-prod, dev, per-client scenario) | Streams, connections, users, permissions | Full separation of definitions, jobs, grants |
| **Stream** | One replication flow (capture → file log → apply) | Connections, tables, monitoring, jobs, events, admin | Operational scope |

Virtual fleets are the answer to both multi-hub use cases: **environment separation** (testing / production / support / sales) and **project separation** (each client's replication scenario on its own virtual fleet). Every virtual fleet separates its streams, connections, users, and permissions from its siblings.

## 3. Global Fleet console

One screen listing every hub server in the company and every virtual fleet on it: state (Live / Frozen / Errors), stream count, connection count, user count, P95 latency, and the viewing user's access level per virtual fleet.

Built for scale (hundreds of fleets):

- **Collapsed by default** — one summary row per fleet (virtual-fleet count, error count); expand to see its virtual fleets. Fleets with errors sort first.
- **Search + filter** — search matches fleet, division, and virtual-fleet names (auto-expands matches); a state filter narrows to Errors / Frozen / Live.
- **Pinning** — a ★ on each fleet row (and on the Fleet view header) adds/removes it from the sidebar. The sidebar shows only pinned fleets plus the current one, with a "Browse all fleets…" entry to reach the console.
- **New fleet** — Global Admins create fleets from the console; a new fleet starts in Enrolling state (enrollment token, mTLS join), the creator becomes its first Fleet Admin, both recorded as ledger events.

Rules:

- **Sight, not touch.** The console is read-only across fleets. Operating on a virtual fleet requires switching into it, which requires a grant on it.
- **Gated by a dedicated permission.** The console reveals the existence and health of every environment in the company — that is sensitive. It is visible only to holders of the repository-level **`FleetViewer`** permission. Everyone else sees a locked screen explaining what to request.
- **No-access rows stay summaries.** A virtual fleet where the viewer has no grant shows name and state only (counts masked), and cannot be entered.

## 4. Admin hierarchy — who can edit whom

Each level of admin can manage admins/grants **at its own level and every level below it — never above**:

| Admin level | Can edit |
|---|---|
| **Global Fleet Admin** | Any account; create fleets; every grant (global, fleet, virtual fleet admins); any connection, table, monitoring, jobs, events — everywhere |
| **Fleet Admin** | Fleet admins and virtual fleet admins **within their fleet**; manage/update/create virtual fleets in it; any connection, table, monitoring, jobs, events — within the fleet. Repository-wide grants are read-only |
| **Virtual Fleet Admin** | Admins of **their own virtual fleet**; manage/update it; any connection, table, monitoring, jobs, events — within that virtual fleet only |

Enforcement in the UI (prototyped):

- Admin panels are not sidebar entries; each screen carries its own admin button — ⚙ Global Admin on the Global console, ⚙ Fleet Admin on the Fleet view, ⚙ VF Admin on the Virtual Fleet overview (Stream Admin stays on the stream node).
- The Permissions view is scope-aware: grants outside the acting admin's scope render with a 🔒 read-only marker and no Revoke action. SuperAdmins bypass tier restrictions (except their own SuperAdmin grant).
- The grant dialog only offers what the level may give: repository-wide permission types (SuperAdmin, SysAdmin, HubCreation, ReadStatistics, FleetViewer) appear only for Global Fleet Admins and SuperAdmins; a Virtual Fleet Admin's dialog is locked to their own virtual fleet.
- A scope note at the top of the Permissions view states explicitly what the current level can and cannot touch, and each admin screen opens with a capability statement for its level.

### Users vs Permissions

- **Users** is the account list — one row per user, only: User, Full name, Status, Last active login, Creation date (+ reset credential / enable / disable / delete actions, multi-select with shift-click, filter box). Disabling a user blocks sign-in but retains grants; deletes and credential resets are ledger events.
- **Permissions** is the single source of who has access where — **one row per attachment** (user × scope), since a user can be attached to multiple fleets and multiple virtual fleets. Columns: User, Fleet, Virtual fleet, Access (permission), Authentication, Status, Last active, Granted (+ revoke). Both panels have text filters.
- The user list an admin sees is itself scoped by grants: Global Admins see everyone in the system; Fleet Admins see accounts attached to their fleet; VF Admins see accounts attached to their virtual fleet. **The grant list is scoped the same way**: a Fleet Admin's Permissions view shows only grants within their fleet (plus repository-wide grants, read-only); a VF Admin's shows only their virtual fleet's.
- Both tables are **sortable by any column** (click header to sort, click again to reverse; default: user ascending). "Last active" sorts by recency, not alphabetically.

### Self-service profile

Every signed-in user has an identity chip in the top-right corner (avatar, username) opening a menu: **Preferences** (edit own full name and email — username and authentication method stay admin-managed; changes are ledger events), **Reset password**, and **Sign out**.

## 5. Permission types (v1 set)

**Repository-wide** (grantable only by Global Fleet Admin):

| Permission | Grants |
|---|---|
| `SuperAdmin` | Everything, everywhere — every fleet and virtual fleet, all admin levels, user management. Implies every other permission. Grantable and revocable only by another SuperAdmin |
| `SysAdmin` | Full access to system, all virtual fleets, user management |
| `HubCreation` | Create new virtual fleets (implies HubOwner on the created ones) |
| `ReadStatistics` | Read fleet-wide statistics, sizing data, sync reports |
| `FleetViewer` | See the Global Fleet console — every fleet and virtual fleet, read-only |

**Per virtual fleet:**

| Permission | Grants |
|---|---|
| `HubOwner` | Full control of the virtual fleet, including access and properties |
| `ReadWrite` | Streams and/or Connections (sub-selectable) — definitions and operations |
| `ReadExecRefresh` | Refresh, compare, start/stop jobs, view objects |
| `ReadExec` | Compare, start/stop jobs, view objects |
| `ReadOnly` | View objects only |

A permission granted to **All Users** is inherited by newly created users by default. Every grant and revoke is an event in the immutable ledger.

## 6. HVR mapping

| HVR | This platform | Verdict |
|---|---|---|
| Hub server | Fleet | Kept, named for what it is |
| Hub (logical, multi-hub on one server) | Virtual fleet | Kept — the isolation model is right |
| No cross-hub-server view | Global Fleet console | **New — the reason this document exists** |
| SysAdmin / HubOwner two-level admin | Three-level admin hierarchy (Global / Fleet / Virtual Fleet), strictly downward-editing | Extended |
| Permissions tab per hub | Scope-aware Permissions view, same grants visible everywhere, editability by level | Extended |
| — | `FleetViewer` permission | New — global sight is its own privilege |

## 7. Open items

- Whether Fleet Admin is a stored permission type (`FleetOwner`) or a derived role (HubOwner on all of a fleet's virtual fleets) — leaning stored, for auditability.
- Cross-fleet aggregation transport: the Global console needs a read-only feed from each hub server (pull over mTLS, air-gap-compatible export for enclaves that cannot be reached live).
- Whether `FleetViewer` should be scopeable to a subset of fleets (per-division global views).
- Whether per-user environment theming (see "Environment theming" section) should optionally be set fleet-wide by a Fleet Admin as a default that users inherit until they customize.

## 8. Environment theming (per user × per fleet)

Operators must always know which environment they are editing — especially production. Theming is a **user preference, scoped per fleet**:

- Each fleet carries an environment for the viewing user: a color (green/blue/red/purple/orange) shown as the banner and UI accent. Prototype defaults: streamsrv-corp = blue Pre Prod, streamsrv-rockets = red Production, streamsrv-radar = green Development.
- Each color keeps its **own label** (defaults: Development, Pre Prod, Production, Staging, Sandbox). Renaming happens on the banner itself, guarded by a prompt ("Rename this banner?" → Edit name / Keep); the field is read-only until editing is confirmed, so no stray-click renames.
- Virtual fleets and streams inherit their fleet's environment. The Global Fleet console is not an environment: neutral banner ("Global Fleet — all environments"), not renamable, and the color picker requires a fleet context.
- **Production forces dark mode.** Entering a fleet whose environment is Production switches the UI to dark automatically; a manual dark-mode toggle covers everything else.
- The color picker and toggles live in the user (identity) menu, section-labelled with the fleet they will affect.
- All of it — per-fleet colors, per-color labels, dark mode, banner visibility — **persists per user**: every user builds their own environment scheme; one user's choices never affect another's view.

## 9. Sign-in, session & workspace

Prototyped local authentication and per-user workspace behavior:

- **Sign-in** — email address + password against local accounts (prototype accepts any password; the field says so). There are no usernames: email is the login identity, distinct from the display full name. Unknown or disabled accounts are refused with a message.
- **Scope-based landing** — a signed-in user lands on the highest scope their grants reach: a global grant (SuperAdmin/SysAdmin/FleetViewer/ReadStatistics/HubCreation or an All Users global grant) → Global Fleet console; else a fleet-level grant → their Fleet view; else a virtual-fleet grant → that Virtual Fleet; else read-only Global.
- **Session persistence** — the session survives page reloads; Sign out clears it and returns to the sign-in screen.
- **Profile persistence** — self-service edits to full name and email (Preferences dialog) apply everywhere immediately (identity chip, menu, Users table) and persist across reloads and sign-out/sign-in, stored per account.
- **Local user creation & editing** — admins create Local users (full name + unique email + password; no username) from their admin panel; the new account receives a starter ReadOnly grant on the creation scope (plus All Users defaults) and persists across sessions. Each user row has an Edit action; changes to full name or email apply everywhere at once and persist across reloads.
- **Identity display** — the console shows full names everywhere (user chip, Users and Permissions tables, grant dialog); email appears as the account identifier. No internal usernames surface in the UI.
- **Resizable sidebar** — sidebar width drags between 180–440 px and is saved per user with the rest of their workspace preferences.

## 10. Connections view (per stream / virtual fleet)

The Connections screen lists the databases and stores a stream (or virtual fleet) replicates between, with their enrolled agents. **Specified in full in `connection.md`** (criteria CON-01..09); summarized here for hierarchy context:

- **Columns (default)** — Connection (name + source/target role pill), Platform, Description, Agent (binary version + platform), Heartbeat (last agent heartbeat, relative), Status (Healthy / Unreachable pill), and a per-row **Test** button that runs a connectivity test (agent reachability, latency, capability-matrix validation) and reports pass/fail with cause.
- **Column chooser** — a Columns dropdown toggles visibility of every column, including hiding the Test button. Hidden-by-default extras: Host / endpoint, Created (date), Created by (full name), Streams (count of streams using the connection), Last test result. The Connection column is locked on.
- **Sorting** — every visible header is click-sortable (click again to reverse) with a visible ▲/▼ indicator. Default order: Connection, descending, indicator shown on load. Heartbeat and Streams sort numerically, not lexically.
- **Filtering** — a filter box under each visible header narrows rows by substring match; filters combine across columns; an empty state appears when nothing matches. The Connection filter also matches the role.
- **Per-user persistence** — column visibility and sort order are stored per account with the user's other workspace preferences and restored at sign-in; each user keeps their own table setup. Filters are session-only.
- **Scoping** — opened from a stream, the list is scoped to that stream's source and target connections; opened at the virtual-fleet level it shows all of the virtual fleet's connections.

## 10A. Where each screen lives

Screens sit at the level that owns the objects they show, and the sidebar mirrors that exactly:

- **Virtual fleet** owns **Connections**, **Jobs**, and **Events** — the databases it replicates between, the work it runs, and its audit trail. In the sidebar these follow the virtual fleet's streams.
- **Stream (stream)** owns **Tables**, **Monitoring**, and **Admin** — what this stream replicates, how it is behaving, and its own settings.
- Under a virtual fleet, streams are listed first in alphabetical order, then Jobs, Events, and Connections.

Each of the three virtual-fleet screens is scoped by the level it was opened from: from a stream it narrows to that stream, from the virtual fleet it covers every stream in it. Counts published in the Global fleet console are derived from the same data those screens read, so a number an operator clicks always matches what they land on.

## 10B. Navigation and history

The console participates in browser navigation rather than trapping the operator inside one page: every screen change — fleet, virtual fleet, stream, connection, admin level, table filter — pushes a browser history entry, so Back and Forward walk the console and Back never dumps the operator out of the application. Modals, filter keystrokes, and toasts deliberately create no entries; Back should undo navigation, not typing.

## 11. Acceptance criteria

| ID | Criterion |
|---|---|
| FLT-01 | Global Fleet console lists every enrolled fleet and its virtual fleets with state, counts, and P95 latency from live feeds |
| FLT-02 | Console visible only to `FleetViewer` / `SuperAdmin`; others get the locked screen and no fleet metadata over the API |
| FLT-03 | No-grant virtual fleets render as name-and-state summaries with counts masked, in UI and API |
| FLT-04 | Search (fleet/division/virtual-fleet), state filter, and error-first sort behave at 200+ fleets |
| FLT-05 | Sidebar pinning persists per user; unpinned fleets reachable only via the console |
| FLT-06 | Fleet creation refused for non-Global Admins; success ⇒ Enrolling state + creator's first Fleet Admin grant, both evented |
| FLT-07 | Virtual-fleet isolation of streams, connections, users, grants proven from a sibling-scoped user |
| FLT-08 | Downward-only admin editing enforced server-side; violations fail and are evented |
| FLT-09 | SuperAdmin edits any grant except their own SuperAdmin grant (another SuperAdmin only) |
| FLT-10 | Permissions is one-row-per-attachment; Users is one-row-per-account |
| FLT-11 | Per-level user visibility derived from grants and identical in UI and API |
| FLT-12 | Permissions view scoped like Users: fleet admins see only their fleet's grants (repository-wide grants read-only); VF admins only their virtual fleet's |
| FLT-13 | Users and Permissions tables sortable on every column with stable default order (user, ascending) |
| FLT-14 | Self-service profile: users edit own name/email only; username and auth method admin-managed; profile changes evented |
| FLT-15 | Environment (color + label) is per user × per fleet; VFs and streams inherit the fleet's environment; Global console shows the neutral non-renamable banner |
| FLT-16 | Banner rename is prompt-guarded (pencil or env change → Edit name / Keep); label field read-only until confirmed; each color keeps its own label |
| FLT-17 | Production environments force dark mode on entry; manual dark toggle covers non-production; theme switch is immediate and complete (no unreadable controls) |
| FLT-18 | All theming choices persist per user across sessions; a second user's session shows their own scheme, not the first user's |
| FLT-19 | Sign-in is by email address (no usernames) and lands the user on the highest scope their grants reach (global → Global Fleet console; fleet → Fleet view; virtual fleet → that VF; none → read-only Global); disabled/unknown accounts are refused |
| FLT-20 | The session persists across page reloads; Sign out clears it and returns to sign-in with no residual access |
| FLT-21 | Self-service profile edits (full name, email) propagate immediately to every surface showing the identity and persist per account across reloads and re-sign-in |
| FLT-22 | Locally created users (full name + unique email, no username) receive a starter ReadOnly grant on their creation scope plus All Users defaults, persist across sessions, and can sign in immediately with their email |
| FLT-23 | Sidebar width is user-resizable within 180–440 px and persists per user alongside their other workspace preferences |
| FLT-24 | Admins can edit any user's full name and email from the Users table; edits propagate to every surface immediately and persist across reloads; duplicate emails are rejected |
| FLT-25 | Full names (not usernames or emails) are the primary identity shown in the user chip, Users table, Permissions rows, and the grant dialog; email is the secondary identifier |
| FLT-26 | Connections view shows Connection (with role), Platform, Description, Agent, Heartbeat, and Status, plus a per-row Test action reporting pass/fail with latency or failure cause |
| FLT-27 | Every Connections column is sortable (toggling asc/desc with a visible indicator; default Connection descending shown on load) and filterable via per-column filter boxes that combine; numeric columns sort numerically |
| FLT-29 | Connections, Jobs, and Events are virtual-fleet screens; Tables, Monitoring, and Admin are stream screens; the sidebar lists a virtual fleet's streams alphabetically, then Jobs, Events, and Connections |
| FLT-30 | Browser Back and Forward walk the console's screens and never leave the application; filters, modals, and toasts create no history entries |
| FLT-31 | Access to enter a fleet or virtual fleet is derived from the operator's grants everywhere it is shown — a SuperAdmin reaches every fleet and virtual fleet, and an ungranted operator is told which grant to ask for |
| FLT-28 | A column chooser adds/removes columns (Host/endpoint, Created, Created by, Streams, Last test; Test button hideable; Connection locked); visibility and sort order persist per user across sessions and are isolated between users |

Registered in `master-traceability-matrix.md` (FLT section, procedures pending).
