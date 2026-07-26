# Filesystem Layout — Design Specification

**Project:** Enterprise CDC Replication Platform
**Document type:** Concept and design specification
**Status:** v1 design; the on-disk contract

---

## 1. Purpose and Positioning

What the software puts on disk is part of its public interface: operators back it up, security teams scan it, accreditors inventory it, and 2 AM incidents get debugged inside it. HVR documents its tree and then *pleads* — "making any changes to hvr_home is strictly prohibited." This specification publishes our tree with the house discipline instead: the install directory is **verifiably immutable** (signed, checksummed, runs read-only), the state directory is **completely enumerated** (a path not in this document is a bug, enforced by sweep), and every directory carries its backup class. The no-hidden-objects promise, applied to the filesystem.

## 2. The Install Directory — small because Rust

HVR's `hvr_home` is a sprawl with reasons: dynamic libraries, database driver trees, SQL template directories, a bundled JRE for its proxy, internal script files, plugin trees, and web UI assets. Static Rust binaries delete most of the list — no `lib/` (static linkage), no `jre/` (no Java anywhere), no `dbms/` template tree (behavior compiled in), no `script/` (the no-generated-scripts rule extends to shipped ones), and no `www/` (UI assets embedded in the hub binary). What remains:

```
install/                        (read-only; identical layout for hub and agent packages)
├─ bin/
│  ├─ replhub                   hub server (hub package)
│  ├─ replagent                 universal agent (agent package)
│  └─ replctl                   CLI (both packages)
├─ share/
│  ├─ docs/                     the complete offline documentation bundle (air-gap promise)
│  ├─ openapi.json              the API contract, versioned with the binary
│  └─ examples/                 sample channel definitions (GitOps-ready)
├─ MANIFEST.sig                 signed checksum manifest of every file above
├─ THIRD-PARTY                  licenses, versions, notices (cargo-deny output, published)
├─ RELEASE                      release notes for this build
└─ VERSION                      version string
```

**Immutability is enforced, not requested.** Binaries verify `MANIFEST.sig` at startup and refuse to run on mismatch (documented override for lab use, itself evented); the recommended deployment mounts `install/` read-only. HVR's "strictly prohibited" paragraph becomes a startup check — the difference between a rule in the docs and a rule in the code.

## 3. The State Directory — completely enumerated

One state root per hub or agent process (default beside the install, override by flag/env). Every entry below carries its **backup class**: ⬛ back up (state you cannot regenerate), ◻ ephemeral (never back up), ◼ policy-dependent (back up per retention needs).

### 3.1 Hub state root

```
state/
├─ config/            ⬛  hub configuration (declarative files the GitOps path also writes)
├─ keystore/          ⬛  envelope-encrypted local secrets: repository bootstrap credential,
│                        hub TLS key material (HVR's 'wallet', named for what it is)
├─ repository/        ⬛  embedded SQLite files (dev/lab mode only; production PostgreSQL
│                        lives outside this tree and is backed up as a database)
├─ filelog/           ⬛  the native file log — HVR's 'router' directory, per hub/channel/
│                        consumer, under the ARC-13 quota; ack-based GC owns deletion
├─ checkpoints/       ⬛  capture positions and retained recovery checkpoints
│                        (HVR's capckp + capckpretain)
├─ enrollment/        ⬛  per-channel table enrollment data (per-table, per CHA-14)
├─ runlogs/           ◼  structured run logs (Jobs §5) + archives, under retention policy
├─ reports/           ◼  sync report archive; also the file-drop delivery root (air-gap sink)
├─ events-forward/    ◼  file-drop forwarder staging for the event ledger (EVT-05)
├─ intermediate/      ◻  compare/refresh working files (prereader intermediates, sort spill)
├─ download/          ◻  large-transfer temporaries
├─ tmp/               ◻  general temporaries (override via the tmp setting)
└─ run/               ◻  pids, sockets, runtime locks
```

### 3.2 Agent state root

```
state/
├─ config/            ⬛  agent configuration (enrollment identity reference)
├─ keystore/          ⬛  the agent's mTLS keypair from enrollment (agent spec)
├─ spool/             ◼  the bounded spool: hub-unreachable buffering and per-transaction
│                        memory-threshold spill (sizing §4.1) — budgeted, alerted
├─ intermediate/      ◻  compare prereader / sort spill (sizing §4.2's worst case lives here)
├─ logs/              ◼  agent-level logs under retention
├─ tmp/               ◻  temporaries
└─ run/               ◻  pids, runtime state
```

### 3.3 What is absent, and why it matters

Three HVR directories have no equivalent here because the mechanisms behind them were designed out — the tree is the proof that the specs meant it:

- **`jobgen/` (generated job scripts)** — does not exist. Behavior lives in signed binaries; the channel spec's "Nowhere: generated scripts" rule is visible as a missing directory.
- **`channels/*/control/` (control files)** — does not exist. Refresh–integrate coordination is per-table boundary state in ordinary bookkeeping (REF-09); there is no blocking-file mechanism to leak.
- **`metering/`** — does not exist. Flat license; nothing to meter.

Also folded rather than removed: HVR's `stats/` state becomes metrics in the repository (one store, one retention policy); `jobcache/` and `jobstate/` become repository rows and event artifacts (query-the-run, not find-the-file); alert configuration is structured settings in the repository, not files.

## 4. Backup and Restore — the one-paragraph runbook

Back up ⬛ always, ◼ per your retention posture, ◻ never. A hub restore is: install (or reuse) the signed package, restore `state/` minus the ephemeral classes, restore the PostgreSQL repository by normal database means, start — capture resumes from `checkpoints/`, integrate resumes from target-side state tables, and the file log's acknowledgment discipline reconciles what the targets already saw. FSL-03 executes exactly this and ends in a clean compare, because a backup procedure that has never been restored is a wish.

## 5. HVR Parity Matrix

| HVR directory concept | This platform | Delta |
|---|---|---|
| hvr_home: bin, lib, dbms, jre, script, www, plugins | `install/`: three static binaries, docs, OpenAPI, examples | Rust deletes the sprawl |
| "Changes to hvr_home strictly prohibited" (docs plea) | Signed MANIFEST verified at startup; read-only mount recommended | Prohibition became a check |
| hvr.3rdparty notices | THIRD-PARTY from the cargo-deny pipeline (ARC-10) | Kept, generated honestly |
| hvr_config as the runtime/config root | `state/` root, every path enumerated with a backup class | Kept, classified |
| wallet (bootstrap security) | `keystore/` — envelope-encrypted, named for what it is | Kept, plainly named |
| router/ transaction files | `filelog/` under ARC-13 quota with ack-based GC | Kept, governed |
| capckp / capckpretain / enroll | `checkpoints/` and `enrollment/` (per-table) | Kept |
| jobgen (generated job scripts) | Does not exist | The no-scripts rule, visible |
| channels/*/control (control files) | Does not exist | REF-09, visible |
| metering | Does not exist | Flat license, visible |
| stats state dir | Metrics in the repository under one retention policy | Folded |
| jobcache / jobstate files | Repository rows and event artifacts | Query-the-run, not find-the-file |
| plugin / plugin_examples trees (agent, transform, authentication, rewrite) | No plugin system in v1 — an honest absence with the extension question parked | Deferred, stated (see §8) |
| logs / logarchives at two levels | `runlogs/` + agent `logs/` under retention policies | Kept, simplified to one level per process |
| hvr_tmp override | `tmp/` with a documented override setting | Kept |

## 6. Test Plan

Phased; standing rule applies. FSL-01's sweep joins the standing no-hidden-objects enforcement: it reruns on every merge that touches any file-writing code path.

| Phase | Focus | Criteria | Environment | Entry condition | Exit condition |
|---|---|---|---|---|---|
| A | Layout conformance and integrity | FSL-01, FSL-02 | Fresh installs + full-exercise lab run | Packaging pipeline built | Sweep clean; tampering detected |
| B | Restore reality | FSL-03 | Lab hub + agents under load | Phase A exit | Documented restore ends compare-clean |

## 7. Test Procedures

### FSL-01 — Complete-tree sweep
**Steps:** (1) Fresh-install hub and agent packages; diff the resulting trees against this document's layouts exactly. (2) Run the full lab exercise suite (activation, CDC under load, refresh, compare with file targets, sync report delivery, event forwarding, a forced spool spill) for a sustained window. (3) Sweep both state roots: every existing path must map to a documented entry; every documented entry must be exercised or explicitly conditional. (4) Assert the three absent directories stayed absent and no script-classified file (executable text) exists anywhere in either tree.
**Expected:** Zero undocumented paths after full exercise; zero missing documented paths; the absences hold; no scripts anywhere.
**Evidence:** Tree diffs (empty), sweep inventory with per-path mapping, script-scan output (empty).

### FSL-02 — Install integrity enforcement
**Steps:** (1) Verify a pristine install passes startup manifest verification. (2) Modify one byte of one binary and one share file; start each; assert refusal with the documented message. (3) Run the full suite with `install/` on a read-only mount; assert zero write attempts (audit at the mount layer). (4) Exercise the documented lab override; assert the override itself lands in the event ledger.
**Expected:** Tampering refused at startup; read-only operation clean; override evented.
**Evidence:** Verification transcripts, refusal captures, mount audit (empty), override event.

### FSL-03 — Backup class restore drill
**Steps:** (1) Under TPC-C load, take the documented backup (⬛ classes + repository dump; deliberately exclude ◻ and one ◼ class). (2) Continue load briefly, then destroy the hub machine (chaos). (3) On a clean machine: install package, restore per section 4, start. (4) Assert capture resumes from restored checkpoints, integrate reconciles via target state tables (no duplicates — the boundary case where backup preceded some acknowledged deliveries), excluded-class absence degrades nothing but its documented function, and the drained system compares clean end to end.
**Expected:** The one-paragraph runbook is sufficient as written; resume exact; zero duplicate or lost changes; compare clean.
**Evidence:** Backup manifest, restore transcript, duplicate-check audit, compare reports.

## 8. Acceptance Criteria (traceability matrix rows)

| ID | Criterion |
|---|---|
| FSL-01 | After full exercise, both trees contain exactly the documented paths — no undocumented files, no missing entries, the three designed-out directories absent, and zero executable scripts anywhere |
| FSL-02 | Startup manifest verification refuses tampered installs; full operation succeeds from a read-only install mount; the lab override is evented |
| FSL-03 | The documented backup classes restore a destroyed hub to exact resume with zero lost or duplicated changes and a clean end-to-end compare |

## 9. Open Questions

The plugin question is the big one this page surfaces: HVR ships agent/transform/authentication/rewrite plugin trees, and customers use them (transforms especially). V1 ships no plugin system — extension via the API and the published file format is the stated answer — but a transform story (and whether it's plugins, WASM modules, or SQL-pushdown expressions) needs a design decision before enterprise deals ask twice; it belongs on the scope board. Path conventions for containerized deployment (state root as a volume; the read-only install as the image layer — which is the natural fit) need one documented pattern. Environment-variable vs flag precedence for the root overrides needs a rule consistent with the settings ladder.
