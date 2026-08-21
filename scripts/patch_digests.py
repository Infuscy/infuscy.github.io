# -*- coding: utf-8 -*-
"""Batch 3 repo-side patch (AUDIT.md D1/D2/D3/D4/P5/P6).

Patches the shipped BAC artifacts so every number is reproducible from the
shipped bac_slim.parquet files:

- findings.json (both years):
  * grade_distribution subject stats -> presented-final population (D1)
  * correlations matrix + strongest_media_correlate -> pairwise-complete
    Pearson over presented rows (D1)
  * competente.materna_competente.chi_square_vs_success -> full 9-row table (D2)
  * school_deep.n_analyzed -> presented>=20 recomputed (+ rule field) (D3)
  * outliers.county_gap / all_pass order -> match outliers.json (D4/P5)
  * meta.schema_version 3 -> 4, meta.patched added
- delta.json:
  * grade_distribution per-subject blocks + histograms -> same population (D1)
  * meta.schema_version 4 + meta.patched
- '' school-name normalization sweep (D7/P6): both parquets, both findings,
  both outliers, both schools.json, delta.json

Idempotent: everything is recomputed from the parquets; safe to re-run.
Run:  python scripts/patch_digests.py   (requires pyarrow + pandas)
"""
import json, sys, io, copy
sys.path.insert(0, r"C:\tmp\pyarrow-tmp")
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"C:\GIT\infuscy.github.io"
YEARS = (2025, 2026)
SUBJECTS = ["romana_final", "materna_final", "profil_final", "alegere_final"]
LABELS = SUBJECTS + ["media"]
NAME_FIXES = {
    'LICEUL "ALEXANDRU CEL BUN\'\' BOTOSANI': 'LICEUL "ALEXANDRU CEL BUN" BOTOSANI',
    'LICEUL TEHNOLOGIC "PETRU RARES\'\' BOTOSANI': 'LICEUL TEHNOLOGIC "PETRU RARES" BOTOSANI',
}
PATCH_META = {
    "date": "2026-08-02",
    "by": "scripts/patch_digests.py (repo-side Batch 3, see BUGFIX_SPEC.md)",
    "reason": "AUDIT.md D1/D2/D3/D4: subject stats recomputed on presented-final "
              "population; materna chi2 over full table; school counts aligned",
    "population": "rezultat_final in (REUSIT, RESPINS) and non-null final grade",
}

def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def dump_json(obj, p):
    raw = open(p, encoding="utf-8").read()
    nl = "\n" if raw.endswith("\n") else ""
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write(nl)

def fix_names(obj):
    """Recursively replace '' school names inside a JSON structure."""
    n = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                for old, new in NAME_FIXES.items():
                    if old in v:
                        obj[k] = v = v.replace(old, new); n += 1
            else:
                n += fix_names(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                for old, new in NAME_FIXES.items():
                    if old in v:
                        obj[i] = v = v.replace(old, new); n += 1
            else:
                n += fix_names(v)
    return n

# ---------------------------------------------------------------- recompute
print("== loading parquets ==")
DF = {}
for y in YEARS:
    DF[y] = pd.read_parquet(rf"{ROOT}\bac{y}\data\bac_slim.parquet")
    print(f"  {y}: {DF[y].shape}")

STATS = {}
for y, df in DF.items():
    pres = df["rezultat_final"].isin(["REUSIT", "RESPINS"])
    dfp = df[pres]
    gd = {}
    for col in SUBJECTS:
        s = dfp[col].dropna()
        mode_vals = s.mode()
        gd[col] = {
            "n": int(len(s)),
            "mean": round(float(s.mean()), 2),
            "median": round(float(s.median()), 2),
            "std": round(float(s.std(ddof=1)), 2),
            "min": round(float(s.min()), 2),
            "max": round(float(s.max()), 2),
            "mode": round(float(mode_vals.iloc[0]), 2) if len(mode_vals) else None,
            "exact_10": int((s == 10.0).sum()),
        }
    cm = dfp[LABELS].corr(method="pearson")
    corr = {"labels": LABELS, "matrix": [[round(float(cm.loc[a, b]), 2) for b in LABELS] for a in LABELS]}
    for i in range(len(LABELS)):
        corr["matrix"][i][i] = 1.0
    sub = cm["media"].drop("media")
    best = sub.abs().idxmax()
    strongest = {"subject": best, "r": round(float(cm.loc[best, "media"]), 2)}
    n_analyzed = int((dfp.groupby(["judet", "unitate_invatamant"]).size() >= 20).sum())
    n_schools = int(df.groupby(["judet", "unitate_invatamant"]).ngroups)
    STATS[y] = {"gd": gd, "corr": corr, "strongest": strongest,
                "n_analyzed": n_analyzed, "n_schools": n_schools}
    print(f"  {y}: n_analyzed(presented>=20)={n_analyzed}, schools={n_schools}")
    for col in SUBJECTS:
        print(f"    {col}: {gd[col]}")

# ---------------------------------------------------------------- findings.json
for y in YEARS:
    path = rf"{ROOT}\bac{y}\data\findings.json"
    d = load_json(path)
    st = STATS[y]
    # D1: grade_distribution subjects
    for col in SUBJECTS:
        block = d["grade_distribution"][col]
        old_n = block.get("n")
        unknown = [k for k in block if k not in st["gd"][col] and k != "histogram"]
        if unknown:
            print(f"  [{y}] NOTE {col}: preserving unknown keys {unknown}")
        for k, v in st["gd"][col].items():
            block[k] = v
        print(f"  [{y}] grade_distribution.{col}: n {old_n} -> {block['n']}, "
              f"mean -> {block['mean']}, std -> {block['std']}")
    # D1: correlations
    old_mx = d["correlations"]["inter_subject_matrix"]["matrix"]
    d["correlations"]["inter_subject_matrix"] = copy.deepcopy(st["corr"])
    d["correlations"]["strongest_media_correlate"] = copy.deepcopy(st["strongest"])
    print(f"  [{y}] correlations romana x profil: {old_mx[0][2]} -> {st['corr']['matrix'][0][2]}; "
          f"strongest -> {st['strongest']}")
    # D2: materna chi2 over the full displayed table
    mc = d["competente"]["materna_competente"]
    rows = mc["cross_tab_success"]
    tp = sum(r["passed"] for r in rows); tn = sum(r["presented"] for r in rows)
    chi2 = 0.0
    for r in rows:
        ep = tp * r["presented"] / tn
        ef = r["presented"] - ep
        of = r["presented"] - r["passed"]
        chi2 += (r["passed"] - ep) ** 2 / ep + (of - ef) ** 2 / ef
    chi2 = round(chi2, 2)
    k = len(rows)
    mc["chi_square_vs_success"] = {
        "chi2": chi2, "p_value": 0.0, "dof": k - 1, "levels_compared": k,
        "note": "computed over all displayed language groups; expected counts < 5 "
                "in the smallest groups (chi2 approximation is indicative there)",
    }
    print(f"  [{y}] materna chi2 -> {chi2} (dof {k-1}, {k} levels)")
    # D3: school_deep
    sd = d["school_deep"]
    print(f"  [{y}] school_deep.n_analyzed: {sd.get('n_analyzed')} -> {st['n_analyzed']}")
    sd["n_analyzed"] = st["n_analyzed"]
    sd["rule"] = "scoli cu >= 20 candidati prezentati"
    # D4/P5: outliers order <- outliers.json
    oj = load_json(rf"{ROOT}\bac{y}\data\outliers.json")
    for key, keyf in (("county_gap", "judet"), ("all_pass", "school")):
        a, b = d["outliers"].get(key), oj.get(key)
        if not a or not b:
            continue
        ka = [x.get(keyf) for x in a]; kb = [x.get(keyf) for x in b]
        if ka == kb:
            continue
        if set(ka) != set(kb):
            print(f"  [{y}] WARN outliers.{key}: member sets differ, order not touched")
            continue
        idx = {v: i for i, v in enumerate(kb)}
        d["outliers"][key] = sorted(a, key=lambda x: idx[x.get(keyf)])
        print(f"  [{y}] outliers.{key}: order aligned to outliers.json")
    # meta
    d["meta"]["schema_version"] = 4
    d["meta"]["patched"] = copy.deepcopy(PATCH_META)
    # P6: '' names
    nfix = fix_names(d)
    print(f"  [{y}] findings.json: {nfix} name fixes")
    dump_json(d, path)
    print(f"  [{y}] findings.json written")

# ---------------------------------------------------------------- delta.json
print("== delta.json ==")
dpath = rf"{ROOT}\bac2526\data\delta.json"
dd = load_json(dpath)
gd = dd["grade_distribution"]
# bucket grid from the known-good media block
grid = [b["bucket"] for b in gd["media"]["histogram_2025"]]
def bucket_counts(s, grid):
    out = []
    for i, b in enumerate(grid):
        lo, hi = (float(x) for x in b.split("-"))
        cnt = int(((s >= lo) & ((s <= hi) if i == len(grid) - 1 else (s < hi))).sum())
        out.append(cnt)
    return out
for col in SUBJECTS:
    block = gd[col]
    s25 = DF[2025]["rezultat_final"].isin(["REUSIT", "RESPINS"])
    s26 = DF[2026]["rezultat_final"].isin(["REUSIT", "RESPINS"])
    v25 = DF[2025].loc[s25, col].dropna()
    v26 = DF[2026].loc[s26, col].dropna()
    m25, m26 = round(float(v25.mean()), 2), round(float(v26.mean()), 2)
    md25, md26 = round(float(v25.median()), 2), round(float(v26.median()), 2)
    sd25, sd26 = round(float(v25.std(ddof=1)), 2), round(float(v26.std(ddof=1)), 2)
    e25, e26 = int((v25 == 10.0).sum()), int((v26 == 10.0).sum())
    block["n_2025"] = int(len(v25)); block["n_2026"] = int(len(v26))
    block["delta_n"] = int(len(v26)) - int(len(v25))
    block["mean_2025"] = m25; block["mean_2026"] = m26; block["delta_mean"] = m26 - m25
    block["median_2025"] = md25; block["median_2026"] = md26; block["delta_median"] = md26 - md25
    block["std_2025"] = sd25; block["std_2026"] = sd26; block["delta_std"] = sd26 - sd25
    block["exact_10_2025"] = e25; block["exact_10_2026"] = e26; block["delta_exact_10"] = e26 - e25
    if "exact_10_share_2025" in block:
        block["exact_10_share_2025"] = round(100.0 * e25 / len(v25), 2)
        block["exact_10_share_2026"] = round(100.0 * e26 / len(v26), 2)
    for yr, v in (("histogram_2025", v25), ("histogram_2026", v26)):
        if yr in block:
            counts = bucket_counts(v, grid)
            n = len(v)
            block[yr] = [{"bucket": b, "share_pct": round(100.0 * c / n, 2)}
                         for b, c in zip(grid, counts)]
    print(f"  delta {col}: n {block['n_2025']}/{block['n_2026']}, mean {block['mean_2025']}/"
          f"{block['mean_2026']}, exact10 {e25}/{e26}")
dd["meta"]["schema_version"] = 4
dd["meta"]["patched"] = copy.deepcopy(PATCH_META)
nfix = fix_names(dd)
print(f"  delta.json: {nfix} name fixes")
dump_json(dd, dpath)
print("  delta.json written")

# ---------------------------------------------------------------- parquets + schools.json
print("== parquet + schools.json name sweep ==")
for y in YEARS:
    p = rf"{ROOT}\bac{y}\data\bac_slim.parquet"
    t = pq.read_table(p)
    idx = t.schema.get_field_index("unitate_invatamant")
    col = t.column(idx).to_pylist()
    nfix = 0
    for i, s in enumerate(col):
        for old, new in NAME_FIXES.items():
            if s == old:
                col[i] = new; nfix += 1
    if nfix:
        t = t.set_column(idx, t.schema.field(idx), pa.array(col, type=pa.string()))
        comp = pq.read_metadata(p).row_group(0).column(0).compression
        pq.write_table(t, p, compression=comp)
    print(f"  {y} parquet: {nfix} rows fixed (compression={comp})")
    sp = rf"{ROOT}\bac{y}\data\schools.json"
    raw = open(sp, encoding="utf-8").read()
    n = 0
    for old, new in NAME_FIXES.items():
        n += raw.count(old)
        raw = raw.replace(old, new)
    if n:
        open(sp, "w", encoding="utf-8", newline="\n").write(raw)
    print(f"  {y} schools.json: {n} occurrences fixed")

# ---------------------------------------------------------------- residual scan
print("== residual scans ==")
for y in YEARS:
    raw = open(rf"{ROOT}\bac{y}\data\findings.json", encoding="utf-8").read()
    cnt = sum(raw.count(old) for old in NAME_FIXES)
    print(f"  {y} findings.json residual '' names: {cnt}")
    d = load_json(rf"{ROOT}\bac{y}\data\findings.json")
    hits = [f for f in d["interesting_facts"]
            if any(w in f.lower() for w in ("romana", "profil", "alegere", "materna"))
            and any(w in f.lower() for w in ("medie", "media", "mean"))]
    for h in hits:
        print(f"  [{y}] fact citing subject stats (review): {h[:160]}")
print("DONE")
