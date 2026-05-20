"""
compute_rq13_kappa.py  (final)
ICC(A,1) — two-way random, absolute agreement, single rater.
Verified against pingouin types: ICC(1,1), ICC(A,1), ICC(C,1), ICC(1,k), ICC(A,k), ICC(C,k)
CI column: "CI95" (not "CI95%")
"""

import pandas as pd
import numpy as np
import os, json, glob

try:
    from pingouin import intraclass_corr
except ImportError:
    print("ERROR: pip install pingouin"); exit(1)

OUT_DIR   = "./outputs/phase6_rq13"
HUMAN_CSV = "./outputs/phase6_rq13/rq13_human_annotations.csv"

CLAUDE_CANDIDATES = [
    "./outputs/phase6/phase6_claude_annotations.csv",
    "./outputs/phase6/phase6_annotations.csv",
    "./outputs/phase6/phase6_annotations_COMPLETE.csv",
]
CLAUDE_CSV = next((c for c in CLAUDE_CANDIDATES if os.path.exists(c)), None)
if CLAUDE_CSV is None:
    found = glob.glob("./outputs/phase6/*.csv")
    CLAUDE_CSV = found[0] if found else None
if CLAUDE_CSV is None:
    print("ERROR: No Claude CSV in ./outputs/phase6/"); exit(1)

os.makedirs(OUT_DIR, exist_ok=True)

human  = pd.read_csv(HUMAN_CSV)
claude = pd.read_csv(CLAUDE_CSV)
print(f"Human  CSV : {HUMAN_CSV}  ({len(human)} rows)")
print(f"Claude CSV : {CLAUDE_CSV}  ({len(claude)} rows)")

# ── Merge ──────────────────────────────────────────────────────
def find_key(df1, df2):
    for k in ["serial_number","manifest_id","story_id","ann_index"]:
        if k in df1.columns and k in df2.columns: return k
    return None

merge_key = find_key(human, claude)
human[merge_key]  = human[merge_key].astype(str).str.strip()
claude[merge_key] = claude[merge_key].astype(str).str.strip()
claude_sub = claude[claude[merge_key].isin(set(human[merge_key]))].copy()
merged = pd.merge(human, claude_sub, on=merge_key, suffixes=("_human","_claude"))
print(f"Merged pairs: {len(merged)}\n")

# ── Detect ICC type and CI column names ───────────────────────
_test = pd.DataFrame({
    "target": [0,1,2,0,1,2],
    "rater":  ["A","A","A","B","B","B"],
    "rating": [1.0,2.0,3.0,1.1,2.1,3.1],
})
_icc = intraclass_corr(data=_test, targets="target",
                        raters="rater", ratings="rating")

# ICC(A,1) = absolute agreement, single rater — what we want
ICC_TYPE = "ICC(A,1)"
if ICC_TYPE not in _icc["Type"].values:
    # Older pingouin fallback
    ICC_TYPE = "ICC2" if "ICC2" in _icc["Type"].values else _icc.iloc[1]["Type"]

# CI column name varies by version
CI_COL = "CI95" if "CI95" in _icc.columns else "CI95%"

print(f"ICC type : {ICC_TYPE}")
print(f"CI column: {CI_COL}\n")

# ── Dimension columns ──────────────────────────────────────────
DIM_MAP = {
    "Species ID":                 ["r_species","species_id"],
    "Habitat":                    ["r_habitat","habitat"],
    "Diet":                       ["r_diet","diet"],
    "IUCN Status":                ["r_iucn","iucn_status"],
    "Overall Ecological Accuracy":["r_overall","overall_accuracy"],
}
DIM_ORDER = list(DIM_MAP.keys())

def resolve(candidates, df, suffix):
    for c in candidates:
        if c+suffix in df.columns: return c+suffix
    for c in candidates:
        if c in df.columns: return c
    return None

dim_pairs = {}
for label, cands in DIM_MAP.items():
    hcol = resolve(cands, merged, "_human")
    ccol = resolve(cands, merged, "_claude")
    if hcol and ccol:
        dim_pairs[label] = (hcol, ccol)

# ── Compute ICC per dimension ──────────────────────────────────
results = {}
print(f"{'='*80}")
print(f"  {'Dimension':<32} {'ICC(A,1)':>9} {'95% CI':>16} {'Pearson r':>10} {'MAE':>7}")
print(f"{'─'*80}")

for label in DIM_ORDER:
    if label not in dim_pairs: continue
    hcol, ccol = dim_pairs[label]
    h = pd.to_numeric(merged[hcol], errors="coerce")
    c = pd.to_numeric(merged[ccol], errors="coerce")
    mask = h.notna() & c.notna()
    h, c = h[mask].values, c[mask].values
    n = len(h)

    df_icc = pd.DataFrame({
        "target": list(range(n))*2,
        "rater":  ["human"]*n + ["claude"]*n,
        "rating": list(h) + list(c),
    })
    icc_table = intraclass_corr(data=df_icc, targets="target",
                                raters="rater", ratings="rating",
                                nan_policy="omit")

    row     = icc_table[icc_table["Type"] == ICC_TYPE].iloc[0]
    icc_val = float(row["ICC"])
    ci      = row[CI_COL]          # list [lower, upper]
    pearson = float(np.corrcoef(h, c)[0,1])
    mae     = float(np.mean(np.abs(h-c)))

    results[label] = {
        "ICC_A1":   round(icc_val,3),
        "CI_lower": round(float(ci[0]),3),
        "CI_upper": round(float(ci[1]),3),
        "pearson_r":round(pearson,3),
        "mae":      round(mae,3),
        "n":        n,
    }
    ci_str = f"[{ci[0]:.3f}, {ci[1]:.3f}]"
    print(f"  {label:<32} {icc_val:>9.3f} {ci_str:>16} {pearson:>10.3f} {mae:>7.3f}")

mean_icc = np.mean([v["ICC_A1"]    for v in results.values()])
mean_r   = np.mean([v["pearson_r"] for v in results.values()])
print(f"{'─'*80}")
print(f"  {'MEAN':<32} {mean_icc:>9.3f} {'':>16} {mean_r:>10.3f}")
print(f"{'='*80}\n")

interp = ("Excellent agreement (Cicchetti 1994)" if mean_icc >= 0.75 else
          "Good agreement (Cicchetti 1994)"       if mean_icc >= 0.60 else
          "Fair agreement (Cicchetti 1994)"       if mean_icc >= 0.40 else
          "Poor agreement — discuss in limitations")
print(f"Interpretation : {interp}")
print(f"Mean ICC(A,1)  : {mean_icc:.3f}")
print(f"Mean Pearson r : {mean_r:.3f}")

# ── Save JSON ──────────────────────────────────────────────────
summary = {
    "n_pairs": len(merged), "merge_key": merge_key,
    "human_csv": HUMAN_CSV, "claude_csv": CLAUDE_CSV,
    "metric": "ICC(A,1) two-way random, absolute agreement, single rater",
    "reference": "Cicchetti (1994)",
    "per_dimension": results,
    "mean_icc_a1": round(mean_icc,3),
    "mean_pearson_r": round(mean_r,3),
    "interpretation": interp,
}
out_path = f"{OUT_DIR}/rq13_icc_results.json"
with open(out_path,"w") as f: json.dump(summary, f, indent=2)
print(f"\nResults -> {out_path}")

# ── LaTeX ──────────────────────────────────────────────────────
rows = ""
for label in DIM_ORDER:
    if label not in results: continue
    v = results[label]
    rows += (f"{label} & {v['ICC_A1']:.3f} & "
             f"[{v['CI_lower']:.3f}, {v['CI_upper']:.3f}] & "
             f"{v['pearson_r']:.3f} \\\\\n")

latex = (
    "\\begin{table}[h]\n\\centering\n"
    "\\caption{Inter-rater agreement between human annotator and automated pipeline "
    "on \\textbf{100} stratified stories (RQ13). "
    "ICC(A,1): two-way random-effects, absolute agreement, single rater "
    "\\citep{Cicchetti1994}.}\n"
    "\\label{tab:rq13_icc}\n"
    "\\begin{tabular}{lccc}\n\\toprule\n"
    "\\textbf{Dimension} & \\textbf{ICC(A,1)} & \\textbf{95\\% CI} "
    "& \\textbf{Pearson $r$} \\\\\n\\midrule\n"
    + rows +
    "\\midrule\n"
    f"\\textbf{{Mean}} & \\textbf{{{mean_icc:.3f}}} & & "
    f"\\textbf{{{mean_r:.3f}}} \\\\\n"
    "\\bottomrule\n\\end{tabular}\n\\end{table}\n\n"
    "% @article{Cicchetti1994,\n"
    "%   author={Cicchetti, Domenic V.},\n"
    "%   title={Guidelines, criteria, and rules of thumb for evaluating normed\n"
    "%          and standardized assessment instruments in psychology},\n"
    "%   journal={Psychological Assessment},\n"
    "%   year={1994}, volume={6}, number={4}, pages={284--290}}\n"
)
latex_path = f"{OUT_DIR}/rq13_table.tex"
with open(latex_path,"w") as f: f.write(latex)
print(f"LaTeX   -> {latex_path}")
print("Done.")