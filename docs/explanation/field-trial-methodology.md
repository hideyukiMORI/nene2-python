# Field Trial methodology — purpose, phases, and terminus

This document explains **why** the Field Trial (FT) loop exists, **how its purpose
changed over time**, and **what counts as "done"**. For the mechanical process
(cadence, report template, DX review personas) see CLAUDE.md §12 and
[`docs/templates/field-trial-report.md`](../templates/field-trial-report.md).

---

## Why the FT loop exists

A Field Trial implements a real workload on top of nene2-python in an **isolated
sandbox** (`/home/xi/docker/nene2-python-FT/ftNNN-*/`), runs the full check suite,
and records the friction points that an implementer actually hits. The goal is to
let documentation and design grow from observation rather than speculation:

- prove the framework API is **stable and ergonomic** across diverse domains;
- surface **friction points** (`F-1`, `F-2`, …) as concrete, fixable observations;
- accumulate **security knowledge** through diagnoses and cracker pentests;
- keep the framework **AI-readable** by documenting decisions.

The lasting output of every FT is its **report in `docs/field-trials/`** — the
sandbox itself is disposable (its `.venv` is regenerable with `uv sync`, and old
sandboxes are periodically cleaned with `ft-status.sh --clean-sandbox`).

---

## Phases (the purpose changed over time)

The FT loop was not a single activity. Its purpose evolved, and #540 exists
precisely because that evolution was never written down.

### Phase 0 — Framework feedback loop (FT1–FT6)

Real sample apps (lunchlog, bookshelf, tasklist, wallet, weather, …) exercised
**framework features**: auth (Bearer/ApiKey), middleware stack, MCP server/client,
transactions, `AsyncUseCaseProtocol`. The aim was to **harden the framework's own
API**. Findings fed directly back into `nene2.*`.

### Phase 1 — Systematic stdlib validation (FT7–~FT202)

Once the core API was stable, the loop pivoted to wrapping **one standard-library
module per FT** in a thin nene2 HTTP layer. Each FT answers: "is the framework's
parse → use-case → response shape ergonomic for *this* domain, and what are the
safe-usage gotchas of *this* module?" This phase produced the bulk of the
[FT INDEX](../field-trials/INDEX.md) and the how-to corpus.

### Phase 2 — Security deepening (FT203+)

From ~FT203 the loop increasingly centered on **security primitives** and the
"dangerous-primitive avoidance" series: `secrets`/`hashlib`/`hmac` (crypto),
`pickle`/`marshal`/`ast.literal_eval`/`eval` (deserialization), `subprocess`
(command injection), `urllib.parse`/`ipaddress` (SSRF), `re` (ReDoS),
`zipfile`/`tarfile`/`zlib`/`gzip`/`lzma` (slip & decompression bombs),
`string.Formatter`/`string.Template` (format-string / SSTI). These FTs have the
highest lasting value because they double as an **audit checklist**.

### Cadence

- **Security diagnosis** (🔒) every FT where `FT % 3 == 0`.
- **Cracker pentest** (🔍) every FT where `FT % 4 == 0`.
- **6-persona DX review** on every FT.

---

## Terminus — what "done" means

The exhaustive stdlib sweep was never meant to run forever, and by Phase 2 the
**security-relevant standard-library surface is covered** (serialization,
compression/archives, parsing/markup, crypto/auth, subprocess, filesystem paths,
network input, regex, numeric input hardening). Continuing to wrap purely
computational modules (`colorsys`, `cmath`, `calendar`, `math`, …) yields
**diminishing returns** against the original purpose.

The FT loop is therefore considered **complete as an exhaustive sweep**, and
transitions to **maintenance + on-demand** mode. A new FT is warranted only when
one of these triggers fires:

1. **New framework capability** needs validation (back to Phase-0-style feedback).
2. **A new dependency** (stdlib or third-party) is *adopted into the framework or
   examples* — validate it before relying on it.
3. **An uncovered security category** is identified (e.g., a new injection class).
4. **Explicit request** from the maintainer.

In maintenance mode the recurring obligations are the monthly
`uv lock --upgrade` → `pip-audit` → test → PR cycle (CLAUDE.md §5), not new FTs.

### How to decide to stop or continue

- If a candidate FT does **not** map to one of the four triggers above, prefer
  **not** to run it — close the loop and spend the cycle on open issues or
  framework features instead.
- "Completion" is a documented decision, not a number. Record the decision in
  [`docs/todo/current.md`](../todo/current.md) (and update the
  [FT INDEX](../field-trials/INDEX.md) footer) when the loop is paused.

---

## Classifying friction and decisions

When an on-demand FT does run, record each friction point (F-1, F-2, …) with a
**kind** and a **decision**, so findings stay consistent and analyzable across
trials rather than as free-form prose.

**Friction kinds**

| Kind | Meaning |
|---|---|
| `docs-gap` | The framework behaves correctly, but the docs/examples didn't make it discoverable. |
| `feature-gap` | A genuinely missing capability the implementer expected. |
| `design-trade-off` | The friction is an accepted consequence of a deliberate design choice. |
| `process-gap` | Tooling/workflow friction (CI, checks, scaffolding), not the API itself. |
| `python-idiomatic-trade-off` | Python-specific friction (Pydantic v2 coercion, async/await, `uv lock`, mypy strict) with no single "right" answer. |

The last kind replaces NeNe's renovation-specific `legacy-preserved`, which does
not apply to a greenfield Python framework.

**Decision kinds** — each friction resolves to exactly one:

| Decision | Action |
|---|---|
| `fix-in-framework` | Change framework/example code in the same FT PR. |
| `document` | Behaviour is correct; add or clarify docs / CLAUDE.md. |
| `keep` | Accept as-is and record the rationale. |
| `defer` | Track as a follow-up Issue with a stated reason — the only case where an Issue outlives the FT PR (CLAUDE.md §12). |

This taxonomy was distilled from the sister-repo governance proposal (#545). The
rest of that proposal (bootstrap script, a dedicated ADR, a separate FT README)
was already covered by CLAUDE.md §12, the existing
[report template](../templates/field-trial-report.md), and this document — or made
low-value by the loop reaching its terminus.

---

## Summary

| Phase | Range | Purpose | Status |
|---|---|---|---|
| 0 — Framework feedback | FT1–FT6 | Harden the nene2 API | ✅ done |
| 1 — Stdlib validation | FT7–~FT202 | Confirm ergonomics + grow docs | ✅ swept |
| 2 — Security deepening | FT203+ | Security primitives as audit checklist | ✅ surface covered |
| Maintenance + on-demand | — | FT only on the 4 triggers; monthly deps | 🔄 current |
