# Bug-fix spec: BAC report pipelines

Audit date: 2026-08-01. Scope: the three upstream report repos (`BAC2025IUNIE`, `BAC2026`, `BAC2526`), whose artifacts get copied into `infuscy.github.io` (`bac2025/`, `bac2026/`, `bac2526/`). All field paths below refer to the shipped `data/findings.json` / `data/delta.json`.

Every bug was verified against the shipped data and the live UIs. Fix order = priority order.

---

## Bug 1 (critical) — Contestation denominator mismatch 2025 vs 2026

**Where:** `analyze/stats.py` in BAC2025IUNIE and BAC2026; `analyze/delta.py` in BAC2526 consumes the digests.

**Symptom:** the delta report's "Contestații" tab shows "2026 schimbate: **130.709**" (all candidates; for materna: 6.856 — the mother-tongue subpopulation, still not the changed count) and "Δ % sus: **−56.86 pp**" (64.2% → 7.34%) — an artifact of comparing different denominators. The chart contradicts its own caption ("~2/3 din contestații duc la creșterea notei" in both years).

**Root cause — the two digests use different semantics for the same fields:**

| field | 2025 digest | 2026 digest |
|---|---|---|
| `contestation_deltas.{subj}.n_changed` | number of changed grades (romana: 16.524) | **total candidates** (130.709; materna: the 6.856 candidates with mother-tongue grades) |
| `contestation_deltas.{subj}.pct_up` | up / changed (67.68) | **up / total** (10.73) |
| `unchanged` | total − changed | total − changed (same semantics) |

**Fix (BAC2026 stats.py):** in the contestation_deltas section compute

```python
n_changed = up + down
pct_up = 100.0 * up / n_changed
```

Do not use the total candidate count as the denominator. `unchanged` stays as-is.

**Expected values after fix (2026):**

| subject | n_changed | pct_up | vs 2025 |
|---|---|---|---|
| romana | 21.222 | 66.07 | 67.68 → −1.6 pp |
| profil | 16.090 | 63.27 | 64.92 → −1.7 pp |
| alegere | 15.131 | 63.39 | 64.20 → −0.8 pp |
| materna | 472 | 66.74 | 62.21 → +4.5 pp |

So the real story is "no material change in contestation behavior" — update the delta narrative accordingly, and the "2026 schimbate" column becomes 21.222 / 16.090 / 15.131 / 472.

**Guard (delta.py):** before diffing, assert for both years: `n_changed == up + down` and `up + down + unchanged == total`. Fail loud on mismatch — this bug class must never silently diff again.

---

## Bug 2 (critical) — Top-school overlap compares top-25 (2025) with top-10 (2026)

**Where:** `rankings.school_by_avg_media.top` in both stats.py digests; `top_school_overlap` in delta.py; the app's "Top 25 școli — persistență" card.

**Symptom:** delta shows "10 în ambele / 15 doar în 2025 / **0 doar în 2026**" and narrates *"Toate cele mai bune 25 de școli din 2026 se aflau deja în top-2025 — vârful este foarte stabil"*.

**Root cause:** the 2026 pipeline's ranking list was truncated to **10** entries (2025 has 25). Every 2026 top-10 school is inside the 2025 top-25, hence the impossible-looking "0 doar în 2026" and the false "very stable" conclusion.

**Fix:** one configurable `TOP_N = 25` used identically in both pipelines. Same drift exists in `rankings.schools_islands_of_excellence` and `school_deep.*` (10 vs 25) — apply the same rule everywhere.

**Guard (delta.py):** assert `len(top_2025) == len(top_2026) == TOP_N` before computing overlap.

**Expected after fix:** `only_2026` ≈ 15 entries; the narrative changes to the true picture (roughly half the top-25 churns year over year — a much more interesting finding than "very stable").

---

## Bug 3 — "5 diferențe care contează" renders only 4 findings

**Where:** BAC2526 app, Investigatia tab findings list (`src/`).

**Symptom:** heading says 5, DOM contains 4 (`h3` count verified live). The 5th finding exists in the code as a data-driven paragraph built from `forma_invatamant` deltas (seral +3.56 pp vs frecvență redusă −4.88 pp) but is never rendered.

**Fix (pick one):**
- (a) restore the 5th finding. Recommended candidate — the presentation-rate drop, which is currently buried in the overview table with zero commentary: `overview.presented_rate` 96.99 → 96.38 (−0.61 pp), absenți 3.178 → 4.662. It pairs naturally with finding #1 (demographic wave, more no-shows).
- (b) change the heading to "4 diferențe".

**Verify:** rendered finding count == number in heading; no empty paragraphs in the findings list.

---

## Bug 4 — Stale "32" perfect-10 count in the 2026 Anomalii tab

**Where:** BAC2026 app, Anomalii tab, "Licee cu cele mai multe note de 10" intro.

**Symptom:** *"Doar **32** de candidați din toată țara au obținut media perfectă — iar aici se concentrează jumătate."* 32 is the 2025 figure; 2026 has **69** (the same app's `interesting_facts` and the delta's "32 → 69" both confirm). Also the "jumătate" claim is off: the listed clusters sum to ~21 of 69 (~30%).

**Fix:** don't hardcode the number — read it from the digest (add a `perfect10_total` field to `overview` or reuse `interesting_facts`) and reword the concentration claim. Grep the app bundle for stray "32" literals.

---

## Bug 5 — `biggest_single_jump` null for 3 of 4 subjects in 2026

**Where:** BAC2026 stats.py contestation_deltas section.

**Symptom:** `contestation_deltas.{profil,alegere,materna}.biggest_single_jump` are `null` (2025 has all four). Consequence: delta's `rankings.biggest_jumps_2026` is `[]`, so the delta report's "Cele mai mari salturi individuale — 2026" section renders blank even though the values exist (`max_abs_swing`: profil 2.9, alegere 3.2, materna 2.15).

**Fix:** populate `biggest_single_jump` for all four subjects (same code path as 2025).

**Guard (delta.py):** assert all four entries non-null in both digests.

---

## Bug 6 (consistency) — `interesting_facts` parity + language

**Where:** both stats.py digests.

**Symptom:** 2025 has 14 facts (in **English**); 2026 has 5 (Romanian). The 2026 digest dropped: contestation stats per subject, top specializare, best limba modernă, widest within-county school gap, strongest correlate. The posts promise "aceeași metodă … pentru comparabilitate directă".

**Fix:** one shared fact generator → same fact dimensions in both years, single language (Romanian — the site's language). Translate the 2025 facts.

---

## Optional hardening (recommended)

1. **Schema versioning:** add `meta.schema_version` to digests (currently only `source` / `generated_by` / `digest_sha256`). `delta.py` refuses to diff mismatched versions — this is the systemic fix for bugs 1, 2, 5.
2. **Label the rank-churn table honestly:** `county_rank_churn` covers top/bottom-15 only by design; the UI should say "top/bottom 15" so the "n/a" rows don't read as missing data.
3. **Bigger rebuild batch:** regenerate both digests *and* the delta in one pass, then diff the delta's narrative numbers before rebuilding the apps — several current narratives (contestations, top-school stability) are wrong because of the metric drift above.

---

## Verification checklist (after rebuild)

```bash
# 1. n_changed == up + down for all subjects, both years
jq '.contestation_deltas | to_entries[] | {k: .key, n: .value.n_changed, up: .value.up, down: .value.down}' bac2026/data/findings.json

# 2. equal ranking list lengths
jq '.rankings.school_by_avg_media.top | length' bac2025/data/findings.json bac2026/data/findings.json   # 25 / 25

# 3. delta sanity
jq '.contestation_deltas.by_subject[] | {subject, n_changed_2025, n_changed_2026, delta_pct_up_pp}' bac2526/data/delta.json   # Δ within ±2 pp
jq '.rankings.top_school_overlap' bac2526/data/delta.json                                                                    # only_2026 ≈ 15
jq '.rankings.biggest_jumps_2026 | length' bac2526/data/delta.json                                                           # 4
```

Live UI checks: delta report — 5 findings rendered, Contestații table ~66% for both years, Clasamente shows a 25/25 overlap, "Cele mai mari salturi individuale — 2026" lists 4 jumps. bac2026 Anomalii — "69" not "32".
