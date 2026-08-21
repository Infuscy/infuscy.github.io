# -*- coding: utf-8 -*-
"""Data integrity guard for the shipped BAC artifacts (Batch 3, AUDIT.md P1).

Recomputes a canary set from bac*/data/bac_slim.parquet and diffs it against
the shipped findings.json / outliers.json / delta.json. Exits non-zero on any
mismatch beyond 2-dp rounding tolerance (0.011).

Definitions (must stay in sync with scripts/patch_digests.py):
- subject-grade population: rezultat_final in (REUSIT, RESPINS) and non-null
  final grade in that subject
- rankings: n = ALL candidates at the school; avg over presented; min-n filter
  on total candidates; ties broken on rounded avg then n desc
- county_gap: schools with presented >= 30

Usage: python scripts/verify_digests.py   (requires pyarrow + pandas)
"""
import json, sys, io, os, glob
if os.environ.get("PYARROW_PATH"):
    sys.path.insert(0, os.environ["PYARROW_PATH"])
import pandas as pd
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOL = 0.011
SUBJECTS = ["romana_final", "materna_final", "profil_final", "alegere_final"]
LABELS = SUBJECTS + ["media"]
fails = []

def check(cid, ok, msg):
    if not ok:
        fails.append(f"[{cid}] {msg}")

def close(a, b, tol=TOL):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

D = {y: load(rf"{ROOT}/bac{y}/data/findings.json") for y in (2025, 2026)}
OUTJ = {y: load(rf"{ROOT}/bac{y}/data/outliers.json") for y in (2025, 2026)}
DELTA = load(rf"{ROOT}/bac2526/data/delta.json")
DF = {y: pd.read_parquet(rf"{ROOT}/bac{y}/data/bac_slim.parquet") for y in (2025, 2026)}

for y, df in DF.items():
    d = D[y]
    pres = df["rezultat_final"].isin(["REUSIT", "RESPINS"])
    dfp = df[pres]
    # --- meta
    check(f"{y}-meta", d["meta"].get("schema_version") == 4 and "patched" in d["meta"],
          f"{y}: meta.schema_version != 4 or meta.patched missing")
    # --- overview
    ov = d["overview"]; rc = ov["result_counts"]
    check(f"{y}-ov-total", sum(rc.values()) == ov["total_candidates"] == len(df),
          f"{y}: overview totals mismatch")
    check(f"{y}-ov-presented", rc["REUSIT"] + rc["RESPINS"] == ov["presented"] == int(pres.sum()),
          f"{y}: presented mismatch")
    check(f"{y}-ov-pass", close(100.0 * rc["REUSIT"] / ov["presented"], ov["national_pass_rate"]),
          f"{y}: pass rate mismatch")
    p10 = int((dfp["media"] == 10.0).sum())
    check(f"{y}-ov-p10", p10 == ov["perfect10_total"], f"{y}: perfect10 {ov['perfect10_total']} != {p10}")
    # --- grade_distribution subjects (presented-final)
    for col in SUBJECTS:
        s = dfp[col].dropna()
        g = d["grade_distribution"][col]
        ok = (g["n"] == len(s) and close(g["mean"], s.mean()) and close(g["median"], s.median())
              and close(g["std"], s.std(ddof=1)) and g["exact_10"] == int((s == 10.0).sum()))
        check(f"{y}-gd-{col}", ok, f"{y}: grade_distribution.{col} not presented-final "
                                   f"(shipped n={g['n']}, recomputed {len(s)})")
    # --- correlations
    cm = dfp[LABELS].corr(method="pearson")
    mx = d["correlations"]["inter_subject_matrix"]["matrix"]
    labels = d["correlations"]["inter_subject_matrix"]["labels"]
    for i, a in enumerate(labels):
        for j, b in enumerate(labels):
            if not close(cm.loc[a, b], mx[i][j]):
                check(f"{y}-corr-{a}-{b}", False,
                      f"{y}: corr {a}x{b} shipped {mx[i][j]} vs {cm.loc[a,b]:.3f}")
    # --- contestation deltas (profil/alegere/materna recomputed exactly)
    pairs = [("profil_nota", "profil_contestatie", "profil_final", "profil"),
             ("alegere_nota", "alegere_contestatie", "alegere_final", "alegere"),
             ("materna_scris", "materna_contestatie", "materna_final", "materna")]
    for cn, cc, cf, subj in pairs:
        c = d["contestation_deltas"][subj]
        m = df[cn].notna() & df[cc].notna() & df[cf].notna()
        delta = df.loc[m, cf] - df.loc[m, cn]
        check(f"{y}-cd-{subj}",
              int(m.sum()) == c["filed"] and int((delta.abs() > 1e-9).sum()) == c["n_changed"]
              and int((delta > 1e-9).sum()) == c["up"] and int((delta < -1e-9).sum()) == c["down"],
              f"{y}: contestation {subj} counts mismatch")
    # --- rankings: first top & bottom entry (n = total candidates, min-n filter)
    rk = d["rankings"]["school_by_avg_media"]
    g = df.groupby(["judet", "unitate_invatamant"]).agg(
        n=("rezultat_final", "size"),
        avg=("media", lambda s: s.dropna().mean())).reset_index()
    for which, lst, asc in (("top", rk["top"], False), ("bottom", rk["bottom"], True)):
        min_n = min(s["n"] for s in lst)
        cand = g[g["n"] >= min_n].copy()
        cand["r2"] = cand["avg"].round(2)
        cand = cand.sort_values(["r2", "n"], ascending=[asc, False], na_position="last")
        # membership + value check (order among 2-dp ties is upstream's choice)
        shipped_keys = {s["key"] for s in lst}
        recomputed_keys = set(cand.head(len(lst))["unitate_invatamant"])
        check(f"{y}-rk-{which}", shipped_keys == recomputed_keys,
              f"{y}: rankings.{which} membership drifted")
        s0 = lst[0]
        row = cand.iloc[0]
        check(f"{y}-rk-{which}-v", close(row["avg"], s0["avg_media"]),
              f"{y}: rankings.{which}[0] value drift")
    # --- county_gap (presented >= 30)
    dfx = df.copy(); dfx["_p"] = pres
    t = dfx.groupby(["judet", "unitate_invatamant"]).agg(
        presented=("_p", "sum"),
        avg=("media", lambda s: s.dropna().mean())).reset_index()
    sch = t[t["presented"] >= 30]
    e0 = OUTJ[y]["county_gap"][0]
    sub = sch[sch["judet"] == e0["judet"]]
    best = sub.loc[sub["avg"].idxmax()]; worst = sub.loc[sub["avg"].idxmin()]
    check(f"{y}-cg", best["unitate_invatamant"] == e0["best"] and worst["unitate_invatamant"] == e0["worst"]
          and close(float(best["avg"] - worst["avg"]), e0["gap"]),
          f"{y}: county_gap[0] mismatch")
    # --- outliers order digest == file (P5)
    for key, keyf in (("county_gap", "judet"), ("all_pass", "school")):
        ka = [x.get(keyf) for x in d["outliers"].get(key, [])]
        kb = [x.get(keyf) for x in OUTJ[y].get(key, [])]
        check(f"{y}-ord-{key}", ka == kb, f"{y}: outliers.{key} order differs digest vs file")
    # --- materna chi2 over full displayed table (P2)
    mc = d["competente"]["materna_competente"]
    rows = mc["cross_tab_success"]
    tp = sum(r["passed"] for r in rows); tn = sum(r["presented"] for r in rows)
    chi2 = sum((r["passed"] - tp * r["presented"] / tn) ** 2 / (tp * r["presented"] / tn)
               + ((r["presented"] - r["passed"]) - (r["presented"] - tp * r["presented"] / tn)) ** 2
               / (r["presented"] - tp * r["presented"] / tn) for r in rows)
    cs = mc["chi_square_vs_success"]
    check(f"{y}-chi2", cs["levels_compared"] == len(rows) and close(chi2, cs["chi2"], 0.05),
          f"{y}: materna chi2 {cs['chi2']} != full-table {chi2:.2f}")
    # --- school_deep.n_analyzed (presented >= 20) (P3)
    n_an = int(dfp.groupby(["judet", "unitate_invatamant"]).size().ge(20).sum())
    check(f"{y}-n_analyzed", d["school_deep"]["n_analyzed"] == n_an,
          f"{y}: school_deep.n_analyzed {d['school_deep']['n_analyzed']} != {n_an}")

# --- delta.json
dov = DELTA["overview"]
check("dl-cand", dov["delta_candidates"] == 130709 - 107812, "delta: candidate delta wrong")
check("dl-pass", close(dov["delta_pass_rate_pp"], 76.98 - 76.56), "delta: pass-rate delta wrong")
for col in SUBJECTS:
    b = DELTA["grade_distribution"][col]
    for yr, y in (("2025", 2025), ("2026", 2026)):
        g = D[y]["grade_distribution"][col]
        check(f"dl-gd-{col}-{yr}", b[f"n_{yr}"] == g["n"] and close(b[f"mean_{yr}"], g["mean"])
              and close(b[f"std_{yr}"], g["std"]) and b[f"exact_10_{yr}"] == g["exact_10"],
              f"delta: grade_distribution.{col} {yr} disagrees with year digest")
    for hkey in ("histogram_2025", "histogram_2026"):
        if hkey in b:
            ssum = sum(x["share_pct"] for x in b[hkey])
            check(f"dl-hist-{col}-{hkey}", abs(ssum - 100.0) <= 1.0,
                  f"delta: {col}.{hkey} shares sum {ssum:.2f}")
check("dl-meta", DELTA["meta"].get("schema_version") == 4, "delta: schema_version != 4")

# --- name hygiene (P6): no quote-artifact school names anywhere in data JSONs
OLD_NAMES = ["CEL BUN'' BOTOSANI", 'PETRU RARES\'\' BOTOSANI']
for f in glob.glob(rf"{ROOT}/bac*/data/*.json"):
    raw = open(f, encoding="utf-8").read()
    hit = [n for n in OLD_NAMES if n in raw]
    check(f"names-{os.path.basename(f)}", not hit,
          f"residual quote-artifact names in {os.path.basename(f)}: {hit}")

# --- posts claims (P3): school counts
posts = {"2025": ("1.443", 1444), "2026": ("1.437", 1438)}
for y, (bad, good) in posts.items():
    for p in glob.glob(rf"{ROOT}/_posts/*bac{y}*"):
        raw = open(p, encoding="utf-8").read()
        check(f"post-{y}", f"{good // 1000}.{good % 1000:03d}" in raw and bad not in raw,
              f"post {y}: school count not updated to {good}")

# ---------------------------------------------------------------- verdict
if fails:
    print(f"VERIFY: FAIL ({len(fails)} problems)")
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("VERIFY: OK — all canary checks pass")
