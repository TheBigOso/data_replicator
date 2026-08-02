# Users & Permissions — Admin Surface

**Project:** Enterprise CDC Replication Platform
**Document type:** UI design specification
**Status:** v1 design — prototyped in `Replicator UI.dc.html` (Admin → Users / Permissions), wireflow in `Users Permissions Wireflow.dc.html`
**Related:** `fleet-hierarchy.md` (admin model), `global-fleet-ui.md` (Global Admin entry), `naming.md`

---

## 1. The split: Users vs Permissions

Two tabs, two different nouns, never merged:

- **Users** = accounts. Who exists: identity, authentication, status, activity.
- **Permissions** = access. One row **per grant attachment** (user × scope × permission) — a user with three grants appears three times. Access control is edited here and only here.

Deleting or disabling a user never edits Permissions; revoking a grant never touches the account. Every mutation on either tab is a ledger event.

## 2. Admin levels — strictly downward

The same two tabs render at all three admin levels, scope-filtered:

| Level | Who opens it | Users tab shows | Permissions can edit |
|---|---|---|---|
| Global Admin | SuperAdmin / SysAdmin | every account in the system | every grant |
| Fleet Admin | Fleet admins | accounts on that fleet (+ global accounts, read-only context) | hub-level grants within its fleet — never repository grants |
| VF Admin | VF admins | accounts on the current VF | grants on the current VF only |

Grants outside the open level's scope still render for context but lock: **🔒 read-only** replaces Revoke. A SuperAdmin can edit anything except revoking their **own** SuperAdmin grant (no self-lockout).

## 3. Users tab

- Header: scope title (e.g. "All users — everyone in the system") + scope note, filter box (users, fleets, roles), **Add user**, and a delete button that appears with a multi-select.
- Sortable columns: Name (initials avatar, `service` badge for service accounts) · Email · Auth · Status · Last active · Created.
- Row actions: **Edit** (profile, starter grants) · **Reset credential** (label varies by auth method) · **Enable/Disable**.
- Sign-in is **email-based — no usernames**. Auth methods: Local (password), SAML (IdP), service tokens.
- **Disabling revokes nothing** — grants stay in Permissions and reactivate on re-enable.
- A collapsible help panel documents each action and each auth method inline.
- A new user inherits every permission granted to **All Users**.

## 4. Permissions tab

- Header: "User access" + filter (grants, scopes), **Add access**. Note: only SysAdmin (any hub) and HubOwner (their hubs) manage access.
- Sortable columns: User · Fleet · Virtual fleet · Permission (pill; hover reveals the concrete grant list) · Auth · Status · Last active · Granted.
- Row action: **Revoke** (danger), or 🔒 read-only outside scope.
- **All Users** is a grantable principal — its rows drive new-user inheritance.

### 4.1 Permission tiers (Add access dialog)

**Repository-level** (whole system):

| Tier | Grants |
|---|---|
| SuperAdmin | Everything, everywhere — implies every other permission incl. FleetViewer. Grantable only by another SuperAdmin |
| SysAdmin | Full system access incl. all hubs and user management |
| HubCreation | Create hubs (implies HubOwner on the created hubs) |
| ReadStatistics | Fleet-wide statistics, sizing, sync reports |
| FleetViewer | See the Global Fleet console, read-only |

**Hub-level** (one scope):

| Tier | Grants |
|---|---|
| HubOwner | Full control of the hub incl. access and properties |
| ReadWrite | Edit objects; opens sub-options when selected |
| ReadExecRefresh | Refresh, compare, start/stop jobs, view |
| ReadExec | Compare, start/stop jobs, view |
| ReadOnly | View only |

## 5. Acceptance criteria

| ID | Criterion |
|---|---|
| UP-1 | Users and Permissions are separate tabs: accounts vs one-row-per-grant-attachment; neither tab's actions mutate the other |
| UP-2 | Both tabs render at Global / Fleet / VF admin levels, scope-filtered; out-of-scope grants show 🔒 read-only instead of Revoke |
| UP-3 | Editing is strictly downward: Fleet Admin never edits repository grants; VF Admin edits only current-VF grants; SuperAdmin cannot revoke their own SuperAdmin |
| UP-4 | Disable revokes nothing; re-enable restores; create/disable/reset/grant/revoke are all ledger events |
| UP-5 | Add access offers repository tiers (SuperAdmin, SysAdmin, HubCreation, ReadStatistics, FleetViewer) and hub tiers (HubOwner, ReadWrite+sub-options, ReadExecRefresh, ReadExec, ReadOnly) |
| UP-6 | All Users grants are inherited by newly created users; the inheritance is stated on both tabs |
| UP-7 | Both tables sort on every column and filter from the header box |
