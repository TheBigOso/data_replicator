# Operational Timelines — Stream, VF, Fleet, Global

**Status:** v1 design — prototyped in `Replicator UI.dc.html` (screens: "Operational timeline", "Virtual fleet timeline"), wireflow in `VF Timeline Wireflow.dc.html`
**Related:** `virtual-fleet-ui.md`, `jobs-ui.md`, `events.md`, `fleet-ui.md`, `global-fleet-ui.md`

Monitoring answers *what is*; the timeline answers **what happened**. An operator staring at "latency 14m" needs to see when the number started moving, what event coincided with it, and which stage of the stream — capture, file log, or apply — owns the delay.

**A latency number without a cause is just a number.** Every other screen reports state: this stream is lagging, that agent is hot, this job is retrying. None of them say *when it started* or *what else was happening at the same moment*. The timeline is the only surface where a throughput dip, a capture stall, an activation, and an agent restart can be seen to be **the same event**.

That is why every "why?" link in the console lands here, and why Jobs and Events both link in at their own timestamp. **The timeline is the join between the open set and the closed set.**

## 1. Four scopes, two shapes

| Scope | Reached from | Shape | Shows |
|---|---|---|---|
| **Stream timeline** | Stream detail → Stream Timeline · the "why? →" link on the latency tile · sidebar Timeline under the stream | Charts | One stream: throughput, capture position lag, checkpoint (apply) lag, file-log backlog — one band per stage |
| **VF timeline** | VF header → VF timeline · sidebar VF Timeline · Fleet timeline card → `VF timeline →` · `timeline →` from Jobs and Events | Charts | Every stream in the virtual fleet combined: total throughput, **worst** capture lag, **total** file-log backlog, plus a per-stream attribution table |
| **Fleet timeline** | Fleet page (inline section) | **Cards** | One card per VF, split triage-first, with CONCERNS / JOBS / CHECKS counts and condition chips |
| **Global** | Global Fleet console | Strip | The needs-triage strip with its severity filter and 90-day history window |

**The shift from charts to cards at fleet level is deliberate.** Combining metrics across *virtual fleets* would mean summing unrelated systems — a VF is an independent namespace, not a shard. Cards preserve that boundary; charts would erase it.

Stream and VF scope share the same time-range selector (1h / 6h / 24h / 7d), the same scrub cursor, and the same event-marker model.

## 2. History bands

Each metric renders as a horizontal band chart over the selected range:

- **Throughput** (rows/min) — the daily flow shape.
- **Capture position lag** — how far the capture job's log position trails the source head. For a stalled capture this grows 1:1 with wall clock, which is exactly the "latency 14m and growing" signature.
- **Checkpoint lag (apply)** — stream scope only: the age of the apply job's last committed checkpoint.
- **File-log backlog** — MB buffered in the hub's file log awaiting apply acknowledgment.

Each band shows the value at the cursor, the peak in view, event markers as dashed vertical rules, and the cursor as a solid rule.

### 2.1 The combining rule — not everything sums

At VF scope each band combines **the way its metric actually behaves**:

| Band | Combines by | Why |
|---|---|---|
| Total throughput | **Sum** | Rows/min across streams genuinely add up |
| Worst capture lag | **Worst-of** | Averaging lag is a lie: nine healthy streams and one stalled one is not "mildly behind", it is broken |
| Total file-log backlog | **Sum** | Megabytes on the hub file store are real bytes and do add |

Getting this wrong is the classic dashboard failure — an averaged fleet metric that stays green while one stream is dead. **Lag is worst-of, never averaged.**

## 3. Event markers

**Two sources, one lane.** Ledger events for the stream(s) in the window — SUSPEND/START, ACTIVATE, COMPARE, REFRESH, DEFINITION CHANGE — appear as markers on every band and as clickable chips below the charts. Alongside them sit two **derived** incident markers that have no operator event: **CAPTURE STALL** (capture stopped — source log unavailable) and **INBOUND BURST** (source burst — backlog began growing). An operator does not care which system noticed.

Clicking a chip jumps the cursor to that moment and all band readouts update together. VF-scope markers are prefixed with the stream name. Markers are **capped and time-sorted** so a busy window stays readable rather than becoming a wall of dots. An empty window says so plainly.

## 4. Scrub cursor and diagnosis

A range slider under the bands positions **one cursor across all bands at once** — that is the whole point. A dip in throughput at the same x as a spike in lag and backlog is one incident, not three.

The readout strip shows the timestamp and each metric's value at that moment, plus the **dominant factor** — whichever of capture lag, checkpoint lag, or backlog-drain time explains most of the end-to-end latency at the cursor. A stalled or suspended stream reads "latency grows 1:1 with wall clock" instead.

**Arriving from a Job or Event lands the cursor at that record's timestamp**, not at "now" — the operator came looking for that moment, not the present.

### 4.1 The diagnosis strip

Above the charts, one **computed sentence** — never a static caption. It states the situation with numbers: at stream scope, what the latency is, what dominates it, when it started, and the projected clear time. At VF scope, the counts (healthy / lagging / error / suspended), then **the single worst stream, why it is worst, and which band it is driving**.

A clean VF gets an equally explicit sentence: *"Nothing needs attention — total throughput follows the usual daily shape."* Silence is never the answer.

## 5. Per-stream attribution table (VF scope)

| Column | Content |
|---|---|
| Stream | Name, opens that stream's own timeline with cursor position preserved |
| Status | Healthy / Lagging / Error / Suspended |
| Latency | Current end-to-end, `—` when errored |
| Backlog | MB buffered now |
| **At cursor** | Rows/min **at the investigated moment** |
| Shape | Throughput sparkline over the window |

**"At cursor" is the column that matters.** Current status tells you the present; the cursor column tells you what that stream was doing at the moment under investigation — which is how a combined dip gets attributed to one stream.

## 6. Infrastructure health

At the top of stream and VF timelines, one card per system the stream crosses, always in this order: **hub · repo database · every source agent · every target agent**. Deduplicated — an agent serving three streams appears once.

| System | Stream scope | VF scope |
|---|---|---|
| Source agent | the stream's capture agent | one card per distinct source agent in the VF |
| Hub system | the stream's hub | the virtual fleet's hub |
| Repo database | the hub's repository database | same |
| Target agent | the stream's apply agent | one card per distinct target agent |

Each card shows **CPU % with core count**, **memory % with installed GB**, and **IO write / IO read MB/s**, each as a bar plus number. Health states: *Healthy*, *Hot* (CPU > 85% or memory > 88%), *Unreachable* (card states last-seen and **hides stats rather than showing stale ones**). Agentless targets (Snowflake, S3) say so plainly rather than reporting fake host metrics — the hub applies directly, so the host stats are the hub's. Each card links to that connection's Server health panel.

**This is the row that closes the loop.** An unreachable source agent next to a stalled capture band is the whole diagnosis, on one screen, without opening a log.

## 7. Per-table flow profile (stream scope)

"Stream health · flow by hour" lists every registered table with its health pill, its **peak window** (peak hour outlined on a 24-cell heat strip, 00–23h), and its **share** of the stream's daily volume. This is the planning surface: an operator scheduling a bulk refresh or compare reads the strip and picks a trough, and sees at a glance which tables carry the stream's volume.

## 8. What-if: activate / deactivate preview (stream scope)

Two cards — **Deactivate** and **Activate** — always both present, each tagged *available*, *no-op*, or *blocked* for the stream's current state. Consequences are stated as rows with projected numbers, in plan language (nothing happens until confirmed):

**Deactivate (active stream):** jobs drain gracefully at checkpoints; capture position held and ages 1:1; file-log frames kept until acked, GC pauses; source-side accumulation ≈ N MB/hour with projections at +1h / +8h / +24h; catch-up cost ≈ N minutes per hour suspended; target untouched.

**Activate (suspended stream):** jobs return to PENDING and cycle on triggers; resume point = held position, N behind head; catch-up ≈ N minutes to re-read the accumulation at the apply drain rate; first apply cycles run hot into the target (~2.8× steady); expected steady-state latency once drained.

**Blocked (errored stream):** activation states that capture cannot restart until the source log is reachable, names the connection to fix, and notes that replication resumes from the held position on its own.

The action button on the *available* card is the same suspend/resume operation as everywhere else — one code path, logged to the ledger.

## 9. Determinism — zooming must not rewrite history

Series are **deterministic per stream** and incidents sit at **absolute wall-clock times**, not at positions relative to the window. Switching 6h → 24h moves the same stall to a new x-coordinate; it does not invent a different stall. An operator can zoom out for context and zoom back in without losing the thing they were looking at.

Same discipline as triage ordering: live data may tick, but **the story must hold still**.

## 10. Prototype notes

Series are seeded per stream, with incident onsets at fixed wall-clock offsets so the red/amber demo streams always carry a readable story. Drain and catch-up math is illustrative, not modeled from real agent throughput. In the product, bands come from the repository's gathered statistics and infra cards from agent heartbeats.

## Rules this surface holds to

1. Lag is worst-of, never averaged.
2. One cursor across all bands — that is the whole point.
3. Incidents sit at absolute times; zooming never rewrites the story.
4. Ledger events and derived incidents share one marker lane.
5. The diagnosis is a computed sentence, never a static caption.
6. Arriving from a Job or Event lands the cursor at that timestamp.
7. Agentless connections say so rather than reporting fake metrics.
8. An unreachable agent hides its stats rather than showing stale ones.

## Acceptance criteria

| ID | Criterion |
|---|---|
| TML-01 | Stream timeline reachable from stream detail (button + latency-tile link) and the sidebar; VF timeline from the VF header, the sidebar, the fleet timeline's VF cards, and `timeline →` links in Jobs and Events |
| TML-02 | Range selector offers 1h / 6h / 24h / 7d; incident onsets hold their absolute time across range changes |
| TML-03 | Stream scope renders four bands (throughput, capture lag, checkpoint lag, backlog); VF scope renders three (total throughput, worst capture lag, total backlog) |
| TML-04 | VF-scope capture lag is the worst stream at every point, never an average; throughput and backlog are sums |
| TML-05 | Ledger events and derived incidents in the window appear as markers on every band and as chips in one lane; clicking a chip moves the cursor to that time and all readouts update together |
| TML-06 | Markers are capped and time-sorted; an empty window states so explicitly |
| TML-07 | Cursor readout reports each band's value at the cursor and names the dominant latency factor |
| TML-08 | Diagnosis strip is computed, not static: stream scope states latency, dominant cause, onset, and projected clear time; VF scope states the counts and names the worst stream and the band it drives |
| TML-09 | Entering the timeline from a Job or Event positions the cursor at that record's timestamp rather than at "now" |
| TML-10 | Infrastructure cards cover hub, repo database, and every distinct source and target agent, deduplicated, showing CPU %+cores, memory %+GB, IO write and read MB/s |
| TML-11 | An unreachable agent's card shows last-seen and no stale stats; an agentless target's card says the hub applies directly |
| TML-12 | Per-stream table shows status, latency, backlog now, rows/min **at cursor**, and a throughput sparkline; clicking a row opens that stream's timeline with cursor position preserved |
| TML-13 | Per-table flow rows show health, peak window (outlined on the 24h strip), and share of stream volume; table name opens table detail |
| TML-14 | Deactivate and Activate cards are both always present, correctly tagged available / no-op / blocked, with projected numbers; the action button invokes the same suspend/resume path used elsewhere and lands in the ledger |
| TML-15 | Fleet scope renders VF cards split triage-first with CONCERNS / JOBS / CHECKS counts and deep-linking condition chips — not combined charts |
