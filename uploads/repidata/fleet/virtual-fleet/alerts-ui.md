# Alerts — Console Surface

**Project:** Enterprise CDC Replication Platform
**Document type:** UI design specification
**Status:** v1 design, prototyped in `Replicator UI.dc.html`; wireflow in `Alert Rules Wireflow.dc.html`
**Companion concepts:** `events.md` (ledger), `scheduler.md` (manager cycle, per-rule tasks), `jobs.md`, `run-history.md`

This document specifies the operator-facing alerts surface: Stream Alerts, Fleet Alerts, acknowledgement, the alert rules and their dialog, schedule & recurrence, the alert logs, and rule management. The alert manager semantics follow HVR-style alerting in our vocabulary.

---

## 1. Two pages, one model

- **Stream Alerts** — one stream's active alerts, on the stream detail. Badge counts and "needs attention" cards count **unacknowledged** alerts only.
- **Fleet Alerts** — every stream's alerts in the virtual fleet on one page, plus the **alert rules** table and **hub health** cards.

Each alert row: severity pill (Critical/Warning), stream link, title + detail, age, **Run log** (jumps to the triggering run), and **Acknowledge**.

## 2. Acknowledge ≠ dismiss

Acknowledging is "I've seen this", not "make it disappear":

- Acknowledged alerts stay on the page, dimmed, with an ACKNOWLEDGED chip and a **Reopen** button; active alerts sort first.
- Only unacknowledged alerts count toward badges and needs-attention cards.
- The **condition** clears the alert; the operator only clears the noise.

## 3. Alert rules — the model

The **alert manager** is a scheduler job that scans hub logs on a configurable cycle and notifies through rules. Each rule:

- **scopes** what it reads — streams and/or connections (unscoped = whole virtual fleet), severity classes (errors + warnings + high latency / errors + latency / latency only), an ignore regex, stream/hub inactivity thresholds, hub-health thresholds (§7b), and an optional blackout window (suppresses the send, not the scan);
- owns **one notification type** — Email, Slack, Amazon SNS, or SNMP traps. A second stream is a second rule;
- optionally **escalates** through unlimited tiers while the alert stays unacknowledged (§5, Escalation tiers);
- is stored as `<name>.conf` under the hub's alerts directory (names lowercase, spaces → `_`).

## 4. Schedule & recurrence

The dialog's SCHEDULE section picks one of three run modes:

| Mode | Behavior | Row summary |
| --- | --- | --- |
| **Every manager cycle** (default) | Rides the shared wake-up | `every cycle · 10m` |
| **On its own interval** | A separate scheduler task — every 30 min / 1 h / 6 h / 12 h; matches found between runs wait for the next run | `every 6 hours` |
| **Daily digest** | One bundled notification at a set time (`07:00`) on chosen day chips (Mo–Su); nothing sends in between and the repeat interval doesn't apply | `daily digest 07:00` / `Mo Tu We Th Fr digest 07:00` |

**Manager cycle.** The cycle itself is set inline in the Fleet Alerts rules header — "the alert manager scans hub logs **every 10 minutes ▾**" — 5/10/15/30/60 min. Persisted, recorded as a DEFINITION CHANGE, effective from the next wake. Changing it never touches own-interval or digest rules — they are their own tasks.

**Gates.** A digest with no digest days can't be saved. Overdue detection is schedule-aware: **⚠ check overdue** appears when a rule hasn't executed within its grace window — 2 h on the cycle, 2× its own interval, 26 h for a digest.

The default rule set showcases all three: `fleet_errors` (Email, every cycle), `ora_erp_latency` (Slack, every cycle, latency-scoped), `nightly_digest` (Email, weekday digest 07:00, whole fleet).

## 5. The dialog — conditions → schedule → notification → escalation → policy

**Conditions.** Scope checkboxes with stream/connection chips · severity radios · latency SLA extra time (seconds past the SLA) · ignore pattern (regex) · stream/hub inactivity minutes · hub-health thresholds (relay backlog over N MB · agents connected below N · frozen-hub watch) · blackout `22:00 → 06:00`.

**Notification.** The type picks the form:

| Type | Needs |
| --- | --- |
| Email | Recipients + SMTP server · optional auth, STARTTLS (pinned cert), from address, port (587 with TLS, else 25) |
| Slack | Incoming webhook URL · optional explicit #stream/@user override; message limit capped at 40 |
| SNS | Topic ARN + IAM access key ID / secret access key |
| SNMP | Hostname (default localhost) · trap port (162) · community · V1/V2C · heartbeats (summary trap even when quiet) |

Secrets are stored on the hub, never echoed back into the dialog.

**Delivery policy.** Message limit (quoted lines per notification, default 1000) · repeat interval (every check → >24 h; the same issue stays silent until it expires) · split events into separate alerts · record an event per notification.

**Escalation tiers.** Tier 1 is the rule's own notification. **+ Add escalation tier** appends unlimited further tiers — each with a group name (Team leads, Executives…), a destination (addresses / #stream / ARN), and a wait in minutes: if nobody acknowledges the alert within the wait, the next tier fires. Waits chain tier-to-tier; acknowledging the alert (or turning the rule off) stops the climb wherever it is. The rules row shows `· N tiers`; the saved DEFINITION CHANGE carries the whole ladder (`tier 2 Team leads after 30m → tier 3 Executives after 60m`); the rule log narrates each escalation and the acknowledgement that stopped it. Snooze/silence hold tier-1 sends — a chain that never started never escalates. Default `fleet_errors` ships with Team leads (30 m) → Executives (60 m).

**Gates.** Name required · Email needs a recipient · Slack the webhook URL · SNS the topic ARN · digest needs ≥1 day · every escalation tier needs a destination. Cancel/✕ discards — nothing saved, nothing scheduled.

**Saved:** row appears with type pill, last check + schedule, scope, severity + repeat + tier count; DEFINITION CHANGE event carries type, scope, severity, schedule, hub health, escalation ladder, repeat, event-per-notification; picked up with no restart — next manager cycle, own interval, or first digest time. Persisted (`repl-alert-rules`, cycle in `repl-alert-cycle`).

## 6. Managing a rule (row actions + ⋮ menu)

- **Disable / Enable** — disabled rules stop executing; row dims, Last check reads *disabled*; test/check/clear only offered while enabled.
- **Send test notification** — see §7a: opens the Test & preview modal.
- **Test & preview (§7a)** — two doors, one modal: ⋮ · *Test delivery & preview* on a saved rule, or **Preview & test** in the dialog footer working on the *unsaved* form. The modal renders the payload from current settings against the live alerts the rule matches — type-specific header fields (From/To/Subject · webhook + stream · topic ARN · trap destination/community/version) over the message body, capped by the message limit; missing required fields show in red. **Send test notification** streams a simulated per-stream delivery trace (SMTP connect → STARTTLS → auth → accepted · Slack POST → HTTP 200 · SNS publish → message id · SNMP trap, UDP no-ack) ending in a **TEST DELIVERED** or **TEST FAILED** verdict — a missing recipient/webhook/ARN fails the way the real stream would. Tests bypass snooze, silence and blackout; the preview never mutates the rule.
- **Hub health × thresholds (§7b)** — rules watch the hub, not just the streams. Conditions: relay backlog over N MB, agents connected below N, frozen-hub watch. Effective thresholds are the tightest across enabled rules; each remembers its watcher. Hub health cards color breached metrics and name the rule (`⚠ backlog over 256 MB (fleet_errors)`); the card dot escalates (amber for backlog/frozen, red for agents); unwatched fleets read *“no alert thresholds set”*. A breach is a live alert row on Fleet Alerts — Warning for backlog/frozen, Critical for agents under minimum — acknowledgeable, badge-counted, and matched by unscoped rules, so digests, previews and rule logs carry hub health too. Hub alerts have no run attached; the rule log states each check (`hub health: relay backlog 352 MB vs 256 MB threshold — OVER.`). Stream-scoped rules never match hub alerts — hub health is fleet-level by definition. The default `fleet_errors` ships with backlog > 256 MB and the frozen-hub watch.
- **Perform alert check now** — executes immediately on any schedule; Last check resets.
- **Clear outstanding errors** — pending errors disregarded; only new errors notify.
- **Duplicate rule** — dialog prefilled as `name_copy`.
- **View rule log** — opens `<name>.out` in the log viewer (docked under the rules table).
- **Delete rule** — removes the `.conf`, recorded on the ledger; its alert history stays on Events.

Stream Alerts has its own **New alert rule** button — same dialog, pre-scoped to that stream.

## 7. Silence & snooze — suppress the send, never the scan

- **Per-rule snooze** — ⋮ menu · Snooze 30m / 1h / 4h / 24h / **∞** (until resumed), or a custom number of hours. The row shows `snoozed · 42m` (or `until resumed`) under Last check; the rule keeps executing on its schedule and keeps logging — only the send is held. Auto-resumes on expiry (∞ resumes only manually), or via **Resume notifications** in the menu. Persisted with the rule.
- **Fleet-wide silence** — **Silence fleet ▾** in the rules header: 30 min / 1 hour / 4 hours / until tomorrow 07:00 / **mute until turned back on** (infinite), or a custom number of hours. While active the button reads `Silenced · 42m` (or `Silenced · ∞`) and a banner above the rules table states the window with a **Resume notifications** action. Covers every rule regardless of schedule; persisted so a reload doesn't un-silence; set and lift are DEFINITION CHANGE events (`repl-alert-silence`, `-1` = infinite).
- **Snooze ≠ disable** — a disabled rule stops executing; a snoozed one only stops sending. Rule logs show `notifications suppressed — rule snoozed until 14:32` (or `fleet-wide silence until …`); the manager log notes an active fleet silence. Send test notification still works while snoozed. Alerts stay on the page — silence mutes streams, not the console.
- **Maintenance blackout windows** — planned, recurring fleet-level periods, distinct from ad-hoc silence: **Maintenance ▾** in the rules header manages named windows, each with day chips (Mo–Su), a `from → to` time range (overnight ranges span midnight), and an enable checkbox. Inside an active window every rule's sends are held — scans and logging continue; the button reads `Blackout · until 06:00`, a banner above the rules table states the window with an **End early — disable window** action, the manager log notes the active window, and rule logs show `notifications suppressed — maintenance blackout "Nightly" until 06:00`. Windows persist (`repl-alert-blackouts`); add / remove / enable / disable are DEFINITION CHANGE events. Tests bypass blackout like they bypass snooze and silence. Suppression precedence in the logs: snooze → fleet silence → blackout. (Separately, a rule can carry its *own* blackout `22:00 → 06:00` in its conditions — §5.)

## 8. The alert logs — two files, one viewer

Docked **in the page** by default — a panel right under the rules table on Fleet Alerts; **⇱ Overlay** floats it over any screen and **⇲ Dock in page** returns it (the choice persists). One log at a time.

- **`alert-manager.out`** — one Checking / Checked pair per cycle across the enabled cycle-scheduled rules; notes rules running on their own schedule. Opened from **Alert manager log**.
- **`<rule>.out`** — one rule's execution history: scoped scan → matched issues → notification sent (destination + quoted-line count) → event recorded — or "0 errors, 0 warnings matched" / "silenced by repeat interval" / "notifications suppressed" (snooze or fleet silence). Digest rules log "digest window closed → bundled N issues → digest sent". Disabled rules log their suspension; overdue rules log the archived-log skip (idle past 5 h scans only the most recent log).
- **Follow / Pause** — follow tails live; pause freezes the view while the file grows. **Download** grabs the whole file; **Copy path** yields `$HUB_CONFIG/hubs/<vf>/alerts/<file>`.

What the log proves: every notification names its trigger — alert → run → event → artifact — so "did it fire, and why not" is answered by the file, not by memory.

## 9. Delivery retry & backoff — a send that fails isn't a send that's gone

Every notification send resolves to **delivered**, **retrying**, or **failed** — never silently dropped.

**Classification.** Each stream error is classified once, at send time:

- **Transient → retry:** SMTP timeout / connection refused / 4xx greylist · Slack HTTP 429 (honors `Retry-After`) or 5xx · SNS throttling / 5xx · SNMP has no ack, so a trap is fire-and-forget — never retried, noted in the log.
- **Permanent → fail fast:** SMTP 5xx reject / bad credentials · Slack 404 (webhook revoked) / 400 · SNS invalid ARN / access denied. No retries; the failure surfaces immediately.

**Backoff curve.** Default: first retry after **30 s**, then **×2** per attempt, capped at **15 min**, max **8 attempts** (~1 h total). Slack `Retry-After` overrides the computed delay when longer. The curve is per-rule (delivery policy section of the dialog): initial delay, multiplier, cap, max attempts.

**Durable queue.** Pending sends persist as `<rule>.pending` under the hub's alerts directory — a hub restart resumes the queue where it left off, honoring the original schedule. **Coalescing:** if a newer notification for the same rule supersedes a pending one (same issue, updated content), the newer payload replaces the older in place — attempt count and next-retry time carry over; the log notes `pending send superseded — payload updated, attempt 3 schedule kept`.

**Failure becomes an alert.** When attempts are exhausted (or a permanent error hits), the rule raises a **delivery-failure fleet alert** — Warning severity, unscoped-rule-matchable, acknowledgeable, badge-counted: `alert delivery failed — fleet_errors → smtp.corp.example: 8 attempts over 58m, last error: connection timed out`. **Loop guard:** a rule never delivers notifications about its *own* delivery failures — another (unscoped) rule may, so a second stream covers the first.

**UI surfaces.**

- **Rules row:** a retrying rule shows `⟳ retrying · attempt 3 · next in 4m` under Last check (amber); an exhausted one shows `✕ delivery failed · 12m ago` (red) until the next successful send or a manual clear.
- **⋮ menu:** **Retry delivery now** (visible while retrying/failed — resets the backoff and sends immediately) · **Discard pending sends** (drops the queue, logged).
- **Rule log:** every attempt is a line — `send attempt 3/8 → smtp.corp.example: connection timed out — transient, next retry in 2m` … `send attempt 4/8 → accepted, 14 quoted lines — DELIVERED after 3 retries`, or `permanent failure (HTTP 404 webhook revoked) — no retry, delivery-failure alert raised`.
- **Test sends** (§7a) never retry — a test reports its first result and stops.

Snooze/silence/blackout interact upstream: a send suppressed by them never enters the queue; a send already queued *before* suppression began keeps retrying (it was owed).

## 10. Acceptance criteria

| ID | Criterion |
| --- | --- |
| ALRUI-01 | Stream Alerts shows one stream's alerts; Fleet Alerts shows every stream's, plus rules and hub health |
| ALRUI-02 | Acknowledged alerts stay visible, dimmed, reopenable; only unacknowledged alerts count toward badges |
| ALRUI-03 | One rule = one notification type; rules are stored as `<name>.conf`, names lowercase |
| ALRUI-04 | Unscoped rules cover the whole virtual fleet; scoped rules filter by stream/connection chips |
| ALRUI-05 | The manager cycle is configurable inline (5–60 min), persisted, ledger-recorded, and drives manager-log spacing and copy |
| ALRUI-06 | A rule runs on the manager cycle, its own interval (30 min–12 h), or as a daily digest at a set time on chosen days |
| ALRUI-07 | Digest rules bundle everything since the previous digest into one send; the repeat interval doesn't apply; ≥1 digest day required |
| ALRUI-08 | Overdue detection is schedule-aware: 2 h on the cycle, 2× own interval, 26 h for digests |
| ALRUI-09 | Email/Slack/SNS gates block save without recipient/webhook/ARN; SNMP defaults suffice |
| ALRUI-10 | Blackout suppresses the send, not the scan; repeat interval silences repeats of the same issue |
| ALRUI-11 | Save logs a DEFINITION CHANGE carrying type, scope, severity, schedule, repeat, event-per-notification; no restart needed |
| ALRUI-12 | Row actions: enable/disable, test notification, check now (any schedule), clear errors, duplicate, view log, delete |
| ALRUI-13 | The log viewer tails `alert-manager.out` and `<rule>.out` with follow/pause, download, copy path; log content always agrees with the rules list |
| ALRUI-14 | Stream Alerts → New alert rule opens the dialog pre-scoped to that stream |
| ALRUI-15 | Per-rule snooze (30m–24h) holds sends only; the rule keeps executing and logging, shows `snoozed · left` on its row, and auto-resumes |
| ALRUI-16 | Fleet-wide silence (30 min–next 07:00) suppresses every rule's sends, shows a banner + header state, survives reload, and is ledger-recorded on set and lift |
| ALRUI-17 | Snooze ≠ disable: disabled stops executing, snoozed stops sending; test notifications bypass snooze; suppression is stated in the rule and manager logs |
| ALRUI-18 | Test & preview renders the type-specific payload from current settings (saved rule or unsaved form) against live matched alerts, with missing required fields flagged |
| ALRUI-19 | The delivery test streams a per-stream trace and ends in DELIVERED or FAILED; missing recipient/webhook/ARN fails; the test never mutates the rule |
| ALRUI-20 | Hub-health thresholds (backlog MB, agent minimum, frozen watch) live on rules; the tightest across enabled rules applies and names its watcher |
| ALRUI-21 | Breached hub metrics color the health card, escalate its dot, and surface as acknowledgeable alert rows counted in badges; unwatched fleets say so |
| ALRUI-22 | Hub alerts carry no run, are matched only by unscoped rules, and every rule log states each hub-health check with OVER/UNDER/ok |
| ALRUI-23 | The log viewer is docked in the page by default (under the rules table); ⇱ Overlay floats it over any screen, ⇲ Dock in page returns it, and the mode persists across reloads |
| ALRUI-24 | Snooze/mute accepts a custom number of hours and an infinite mute (∞ / “until turned back on”) per rule and fleet-wide; infinite resumes only manually |
| ALRUI-25 | Escalation tiers are unlimited (+ button); each has a group label, destination, and per-tier unacknowledged wait; a tier without a destination blocks save |
| ALRUI-26 | Escalation fires tier by tier while the alert stays unacknowledged; acknowledging or disabling stops the chain; the rule log narrates each step and the row shows the tier count |
| ALRUI-27 | Fleet maintenance windows (name, day chips, from→to, overnight-safe) hold every rule's sends while active, never the scan; active window shows header state + banner with end-early; windows persist and every change is ledger-recorded |
| ALRUI-28 | Stream errors classify as transient (retry) or permanent (fail fast); SNMP traps never retry; classification is stated in the rule log |
| ALRUI-29 | Retry backoff defaults to 30 s ×2 capped at 15 min, max 8 attempts; per-rule tunable; Slack Retry-After honored when longer |
| ALRUI-30 | Pending sends persist in `<rule>.pending` across hub restarts; newer notifications coalesce over pending ones keeping the attempt schedule |
| ALRUI-31 | Exhausted or permanent failures raise a Warning delivery-failure fleet alert matched by unscoped rules; a rule never delivers its own failure (loop guard) |
| ALRUI-32 | The rules row shows retrying (attempt + next-in) and failed states; ⋮ offers Retry delivery now and Discard pending sends; every attempt is a rule-log line; tests never retry |
