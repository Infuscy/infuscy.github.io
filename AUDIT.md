# Full Codebase & BAC Data-Methods Audit

Audit date: 2026-08-02 (this repo, working tree at `036bf8c`).
Scope: the Jekyll site layer, the three shipped report apps (`bac2025/`, `bac2026/`, `bac2526/`), and above all the **investigative and data-analysis methods and results** for the BAC reports — independently re-verified against the raw candidate-level data (`bac*/data/bac_slim.parquet`).

Method: black-box recomputation. Every headline number was recomputed from the raw parquet with independent code (Python/pandas) and diffed against the shipped digests. 180 digest-internal consistency checks + 98 recomputation checks + the full `BUGFIX_SPEC.md` regression checklist were executed. Scripts: `C:\tmp\bac_audit\audit_digest.py`, `audit_parquet.py`, `audit_parquet_b.py`, `audit_interesting.py` (kept outside the repo; check logs in `digest_checks.json`, `parquet_checks.json`, `parquet_checks_b.json`, `interesting.json`).

---

## 1. Executive summary

- **All 10 bugs from `BUGFIX_SPEC.md` are verifiably fixed in the shipped artifacts** (schema v3 digests, corrected denominators, 25/25 rankings, ascending bottoms, real Cohen's d inputs, diacritic folding, n≥30 rules, full churn table). The spec's expected post-fix values match the shipped data exactly.
- **The site layer is clean**: build verifies (3 cards, 3 sequential modals, `| raw` intact, links resolve), jQuery-3 compatible JS, GDPR promises match reality, CSP identical across the three report apps, all referenced assets/data exist.
- **One substantive integrity problem was found**: the per-subject `grade_distribution` and `correlations` sections of both digests **cannot have been computed from the shipped `bac_slim.parquet`** — for romana the shipped `mean × n` is *less than the sum of the non-null grades alone*, which is mathematically impossible for any superset of that data. The evidence points to the digests having been computed from a different data state (upstream full parquet, pre-contestation grades, absentees encoded as 0) than the slim extract shipped next to them. User-visible consequence: the reports' live SQL console contradicts the digest charts.
- **Everything else recomputes**: overview counts/rates, perfect-10 counts (32/69), all contestation-delta counts (exact, both years), rankings membership and values, county gaps, outlier tables, and the reporter deep-dives (Ilfov, Mehedinți, dead zone, math pass) reproduce exactly once the pipeline's definitions are pinned.
- **Ten data findings worth surfacing** are documented in §4 (Ilfov as the worst county both years, 2,034 candidates failing with media ≥ 6, contestation intensity up ~2× the demographic wave, the vocational wave absorbing 40% of growth, threshold pile-ups, and more).

---

## 2. Verified checks — summary

| Area | Checks | Result |
|---|---|---|
| Jekyll layer (posts, includes, build, links, CSP, GDPR) | 15 | all pass |
| Digest internal consistency (both years: overview, contestations, rankings, repeaters, competente, percentiles, correlations, facts, outliers, meta) | 180 | 174 PASS, 0 FAIL, 6 WARN (all explained below) |
| Recomputation from parquet (overview, grade stats, contestations, correlations, rankings, counties, forma/limba, outliers, deep-dives) | 98 | 85 PASS, 13 FAIL → all 13 traced to definition differences or real discrepancies (see §3) |
| `BUGFIX_SPEC.md` regression checklist (bugs 1–10) | 10 | 10/10 fixed |
| Bundle review (hardcoded literals, truncation, fallbacks, CSP, asset refs) | 12 | pass (2 copy nits, §3-D5/D6) |

Highlights of what reproduces **exactly** from raw data:

- Overview 2025/2026: totals, result counts, presented, pass rates (76.56 / 76.98), elimination rates, perfect-10 = **32** (2025) / **69** (2026), `media == 10.0` exact.
- Contestation deltas for profil/alegere/materna, **every count** (filed/changed/up/down), mean/median delta, max swing — both years (e.g. 2026 profil: filed 16,941, changed 16,090, up 10,180, down 5,910).
- Rankings: top-25 and bottom-25 membership **and** values (min-n filter on total candidates), county top/bottom (ties broken alphabetically after rounding to 2 dp), `county_gap` reproduces exactly with a `presented ≥ 30` school filter.
- `outliers.json`: every entry's n/presented/passed/avg/pass-rate/tens verified against the recomputed school table; `perfect10_clusters` counts match.
- `reporter_deepdive`: `county_math_pass` = MATEMATICA MATE-INFO ∪ MATEMATICA ST-NAT (exact, e.g. GR 2025: 82/135 = 60.74); `neprezentat_schools`, `ilfov`, `mehedinti` core stats; `dead_zone` bins = **all presented candidates** per media bin (not only RESPINS).
- `delta.json`: candidate delta 22,897; pass-rate delta +0.42 pp; contestation Δ within ±2 pp (materna +4.53 as the spec predicted); churn table identities (`delta_avg_media == avg26 − avg25`); IF/MH/TM ranks 16→16, 17→17, 30→30; overlap 19/6/6 internally consistent.

---

## 3. Discrepancies

### D1 (HIGH) — Digest subject-level grade stats are not computable from the shipped data

`grade_distribution.romana_final/profil_final/alegere_final/materna_final` in **both** digests:

- `n` counts **all** candidates in the subpopulation, not grade holders: romana/profil/alegere n = 107,812 / 130,709 (total candidates, incl. 3,178/4,662 NEPREZENTAT and 63/70 ELIMINAT); materna n = 6,201 / 6,856 although only 6,172 / 6,820 rows have any materna grade in slim.
- The shipped **means are impossible** given slim's values: for romana 2025, `mean × n = 107,812 × 6.95 = 749,293` but the sum of non-null `romana_final` alone is ≈ 751,900. No non-negative imputation of the missing 1,270 values can produce the shipped mean.
- The shipped **medians match pre-contestation (initial-grade) distributions** over all candidates with missing → 0 (profil 7.35, materna 7.60/7.75 — exact), while `media` stats match presented-final exactly. I.e. the subject entries behave like **initial (pre-contestation) grades over all candidates, absentees as 0**, under a `_final` label.
- `std` values (1.98/2.49/2.37 vs true presented-final 1.71/2.16/1.98) are inflated by the zero-filled absentees and still not exactly reproducible from slim.

**Root cause (inferred)**: digests were generated from the upstream full parquet (`meta.source`), which is not shipped and evidently differs from the shipped slim extract (extra grade rows and/or pre-contestation values). The two artifacts shipped side-by-side in each report disagree.

**User impact**: the reports' own DuckDB SQL console runs over the slim parquet — `SELECT AVG(romana_final) …` returns ≈ 7.06 (non-null) while the digest chart says 6.95. The report contradicts itself.

**Same root cause**: `correlations.inter_subject_matrix` is systematically attenuated vs any recomputation (12/25 entries off by > 0.01; romana×profil shipped 0.65/0.66 vs 0.749 recomputed; profil×media 0.88 vs 0.922). The materna pairs (few contestation changes) match — consistent with the digest having used pre-contestation grades.

### D2 (MEDIUM) — `competente.materna_competente` chi² doesn't match its own table

Shipped chi² = 243.61 (2025) / 231.41 (2026) with `levels_compared: 4`, but the cross-tab displayed next to it has **9** language rows (full-table chi² = 260.10 / 252.27). Brute-force subset search proves the shipped value was computed over exactly {LIMBA GERMANA, LIMBA MAGHIARA (UMAN), LIMBA MAGHIARA (REAL), LIMBA UCRAINEANA} — the 4 largest groups — in **both years** (a consistent min-n rule, but undocumented, and the displayed table implies otherwise). Digital and romana chi² values match their tables.

### D3 (LOW) — School-count claims off by one

- Posts: "1.443 de școli" (2025) / "1.437 de școli" (2026); slim gives **1,444 / 1,438** distinct (judet, school) pairs.
- `school_deep.n_analyzed` = 1,137 / 1,206; the `presented ≥ 20` rule that otherwise matches gives 1,138 / 1,207.

A consistent ±1 pattern — almost certainly the upstream full data differing by one school/row from slim (the two `''`-quote names are *not* duplicates; merging them changes nothing). Cosmetic but it means the site's own numbers can't be reproduced from the site's own data.

### D4 (LOW) — Tie-break order differs between digest and `outliers.json`

`county_gap` (both years) and `all_pass` (2026): same members and values, different order among equal sort keys. UI reads `outliers.json`, so digest and UI can list the same counties/schools in different order.

### D5 (LOW) — Hardcoded year-specific number in the delta app

Finding #4 renders "Ziua a rămas stabilă la **~77.7%**" — the 2026 value (77.71); 2025 was 77.36. The qualitative claim (stable) is right, but the literal is data that should come from `family_delta`/`forma` fields (same class as the spec's Bug 4).

### D6 (INFO) — Copy precision in the delta app

- "Notele perfecte s-au dublat" — 32 → 69 is +116% ("more than doubled").
- The spec's predicted top-25 churn ("roughly half churns") did not materialize: actual overlap is 19 both / 6+6 — the top **is** very stable (the original narrative was right for the data, wrong for the buggy comparison).

### D7 (INFO) — Spec's mojibake issue is already resolved in shipped data

`BASARABË®`-style names: **0 rows** in either slim parquet. Remaining cosmetic artifact: two Botoșani schools use `''` as closing quote (69 rows 2025 / 102 rows 2026, no duplicate-name collisions).

---

## 4. "Interesting findings" (data, evidence-backed)

1. **Ilfov paradox — worst county in Romania, both years.** IF pass rate 59.18% (2025) / 58.78% (2026) vs national 76.56/76.98 — ~18 pp below, and dead last of 42 counties both years, with a *tiny* candidate population (1,092 / 1,368 — the capital's gravitational pull). County spread 2026: CJ best 87.2%, IF worst 58.78% — a 28.4 pp gap.
2. **The dead-zone paradox.** 2,034 candidates (2026) / 1,840 (2025) **failed with an average ≥ 6.00** — max failing media 7.85/7.94 — because a single subject < 5 fails the whole diploma. Meanwhile 376/285 passed with media ≈ 6.00. "Media" is a misleading success indicator; the reports could say this explicitly.
3. **Contestation intensity grew ~2× faster than the candidate wave.** Filed: profil +45.1%, alegere +50.2%, materna +57.2%, romana +28.9% (16,988 → 21,896) — total ≈ 39.7k → 55.4k (+39.6%) vs +21.2% candidates. Success rate stayed ~66% (romana 67.68 → 66.07): the system absorbs them consistently.
4. **The wave was vocational.** Of the +22,897 candidates, 40.5% went to TEHNIC/VOCATIONAL (avg media 6.23, lowest family), yet the national pass rate held (+0.42 pp). Divergence inside non-day forms: SERAL +3.56 pp vs FRECVENTA REDUSA −4.88 pp.
5. **Threshold pile-ups.** Romana grades cluster at exactly 5.00 (1.82%/1.69% of presented — ~2.3× the rate at 7.00); the media distribution is asymmetric around 6.00 ([5.80–6.00) = 2.53% vs [6.00–6.20) = 3.84%). Profil/alegere have large exact-10.00 spikes (profil 3.73%/3.05% — thousands of perfect subject scores, concentrated in the technological track's easier variants).
6. **The perfect-10 doubling is breadth, not concentration.** Schools with ≥ 1 perfect media: 27 → 51; top-5 schools' share fell 31.2% → 26.1%. (2026 leader: CN "Sfântul Sava" B, 6.) This argues against any single-source artifact.
7. **School-level volatility.** Among 952 schools with n ≥ 30 both years: biggest fall LT "Tata Oancea" Bocsa (CS) −1.28 avg / −27.4 pp; biggest rise LT Sebeș (AB) +1.40 / +36.9 pp — mostly small technological licees, consistent with cohort noise rather than systemic effects.
8. **Eliminations concentrate.** 2025: Mehedinți alone 12 of 63 (19%). 2026: București top with 7. About half of eliminated candidates have a romana grade (sat at least one exam).
9. **"Absent" candidates with grades — explained.** 54–61% of NEPREZENTAT have a romana final grade (mean ≈ 4.85): they sat romana, then skipped the rest. This is the population that poisons D1's stats.
10. **Structural subvariant gap.** Hardest alegere subject: BIOLOGIE VEGETALA SI ANIMALA 5.12/5.35 (n ≈ 11–14k!) vs easiest CHIMIE ORGANICA 8.88/9.00 — a ~3.9 pp gap between choices with huge n. Same subject, different variant: FIZICA TEO 8.81 vs FIZICA TEH 5.94.

---

## 5. Limitations

- Upstream pipeline repos (`stats.py`, `delta.py`, full parquets) are not in this repo — the method review is black-box, against shipped artifacts; `BUGFIX_SPEC.md` served as the documentation of intent.
- The slim parquet lacks candidate IDs, romana initial grades, competence levels, and the repeater flag, so `competente`, `repeaters_vs_first`, and romana contestation deltas were verified **internally only** (identities hold; group sums match presented counts; Welch t and Cohen's d recompute from shipped n/mean/std).
- D1/D2 root cause is inferred from arithmetic necessity, not observed directly (the full upstream parquet isn't available here).

## 6. Prioritized fix plan

1. **P1 — Regenerate digests from the same data state as the shipped slim parquet** (or ship the full parquet). Resolves D1 + the correlations attenuation. Add a CI guard: recompute a canary set (subject means/stds/n, 3 correlations, 2 ranking entries) from the slim parquet and fail on |Δ| > 0.01.
2. **P2 — Document or fix the materna chi² population** (compute over all levels with a stated min-n grouping, or label the table "top 4 languages"). Resolves D2.
3. **P3 — Align school counts** between posts, `school_deep.n_analyzed`, and the shipped data; state the counting rule (all candidates vs presented ≥ 20). Resolves D3.
4. **P4 — Delta-app copy**: replace the hardcoded "~77.7%" with a digest-driven value; "s-au dublat" → "s-au mai mult decât dublat". Resolves D5/D6.
5. **P5 — Unify tie-break ordering** between digest and `outliers.json` serialization (same secondary sort key). Resolves D4.
6. **P6 — Cosmetic**: normalize the two `''` school names in the source data at the next re-scrape.

## 7. Verification artifacts

- `C:\tmp\bac_audit\audit_digest.py` → `digest_checks.json` (180 checks)
- `C:\tmp\bac_audit\audit_parquet.py` / `audit_parquet_b.py` → `parquet_checks.json` / `parquet_checks_b.json` (98 checks)
- `C:\tmp\bac_audit\audit_interesting.py` → `interesting.json` (§4 evidence)
- BUGFIX_SPEC checklist run verbatim (jq) — output captured in session log

---

## 8. Remediation log (Batch 3, 2026-08-02)

All six fix-plan items implemented repo-side (see `BUGFIX_SPEC.md` Batch 3 for upstream porting notes):

| Item | Discrepancies resolved | Resolution |
|---|---|---|
| P1 | D1 | `grade_distribution` subjects, `correlations`, and `delta.json` per-subject blocks + histograms recomputed on the presented-final population; `schema_version` → 4 + `meta.patched` |
| P1 guard | regression prevention | `scripts/verify_digests.py` (canary recomputation, exits non-zero) + `.github/workflows/verify-data.yml` (runs on data pushes) |
| P2 | D2 | materna chi² over the full 9-row table (260.10 / 252.27, dof 8) with caveat note |
| P3 | D3 | posts → 1.444 / 1.438 schools; `school_deep.n_analyzed` → 1.138 / 1.207 + published counting rule |
| P4 | D5, D6 | bundle: ZI sentence now data-driven (`a.ZI.pass_rate_2025/2026`); heading corrected to "s-au mai mult decât dublat"; `node --check` clean |
| P5 | D4 | digest `outliers.county_gap` (both years) + `all_pass` (2026) reordered to match `outliers.json`; order equality guarded |
| P6 | D7 | `''` school names normalized in both parquets, findings, schools.json (JSON-escape-aware sweep; raw-text replace alone silently misses `\"`) |

Post-patch verification: `verify_digests.py` → OK; digest suite 176/177 PASS (single benign heuristic WARN); grade-distribution and correlation recomputation checks now PASS against the shipped parquets.
