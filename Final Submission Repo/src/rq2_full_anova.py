import os
import numpy as np
import pandas as pd
from scipy import stats


import os
# ---------------------------------------------------------------------------
# Portable path resolution. This script lives in <repo>/src/.
# All data, figures, and reports live in sibling folders of src/.
# When dropped into "C:\\Users\\kraam\\Downloads\\Final Submission Repo\\src"
# on the local machine, these paths resolve there automatically. To override,
# set the FINAL_SUBMISSION_DIR environment variable before running.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
FS     = os.environ.get("FINAL_SUBMISSION_DIR", os.path.dirname(_HERE))
FS_DIR = FS
DL     = os.path.dirname(FS)
DATA   = os.path.join(FS, "data")
FIG    = os.path.join(FS, "figures")


FS = os.path.join(DL, "Final Submission", "data")
IN = os.path.join(FS, "prescribers_full_npi.csv")

print("Loading full NPI file...")
df = pd.read_csv(IN)
print(f"  Rows: {len(df):,}, unique NPIs: {df['Prscrbr_NPI'].nunique():,}")

# Aggregate to one row per NPI (collapsing duplicate state/specialty splits if any)
prescriber = df.groupby("Prscrbr_NPI", as_index=False).agg(
    state=("Prscrbr_State_Abrvtn", "first"),
    specialty=("Prscrbr_Type", "first"),
    total_clms=("total_clms", "sum"),
    total_cost=("total_cost", "sum"),
    brand_clms=("brand_clms", "sum"),
    brand_cost=("brand_cost", "sum"),
)
prescriber["brand_share"] = np.where(
    prescriber["total_clms"] > 0,
    prescriber["brand_clms"] / prescriber["total_clms"],
    np.nan,
)

# Apply same 20-claim filter as interim
clean = prescriber.dropna(subset=["brand_share", "state"]).copy()
clean = clean[clean["total_clms"] >= 20]
print(f"Analyzable prescribers (>=20 annual claims): {len(clean):,}")

# Per-state aggregates
state_brand = clean.groupby("state").agg(
    n_prescribers=("Prscrbr_NPI", "nunique"),
    mean_brand_share=("brand_share", "mean"),
    median_brand_share=("brand_share", "median"),
    std_brand_share=("brand_share", "std"),
    total_clms=("total_clms", "sum"),
    brand_clms=("brand_clms", "sum"),
    total_cost=("total_cost", "sum"),
    brand_cost=("brand_cost", "sum"),
).reset_index()
state_brand["weighted_brand_share"] = state_brand["brand_clms"] / state_brand["total_clms"]
state_brand = state_brand.sort_values("weighted_brand_share", ascending=False)

# Keep states with >=100 prescribers (much higher threshold now that we have full data)
qualifying = state_brand[state_brand["n_prescribers"] >= 100]["state"].tolist()
print(f"States with >=100 prescribers: {len(qualifying)}")

groups = [clean.loc[clean["state"] == s, "brand_share"].values for s in qualifying]
F, p = stats.f_oneway(*groups)
all_vals = np.concatenate(groups)
gm = all_vals.mean()
ss_total = np.sum((all_vals - gm) ** 2)
ss_between = sum(len(g) * (g.mean() - gm) ** 2 for g in groups)
eta_sq = ss_between / ss_total
print(f"ANOVA: F = {F:.2f}, p = {p:.4g}, eta-squared = {eta_sq:.4f}")

H, p_kw = stats.kruskal(*groups)
print(f"Kruskal-Wallis: H = {H:.2f}, p = {p_kw:.4g}")

state_brand.to_csv(os.path.join(FS, "rq2_state_brand_share.csv"), index=False)
pd.DataFrame([
    {"test":"One-way ANOVA","outcome":"prescriber brand_share",
     "grouping":"state","k_groups":len(qualifying),"n_total":len(all_vals),
     "F_statistic":F,"df_between":len(qualifying)-1,
     "df_within":len(all_vals)-len(qualifying),"p_value":p,"eta_squared":eta_sq},
    {"test":"Kruskal-Wallis H","outcome":"prescriber brand_share",
     "grouping":"state","k_groups":len(qualifying),"n_total":len(all_vals),
     "F_statistic":H,"df_between":len(qualifying)-1,
     "df_within":np.nan,"p_value":p_kw,"eta_squared":np.nan},
]).to_csv(os.path.join(FS, "rq2_anova_results.csv"), index=False)
print(f"Saved RQ2 outputs to {FS}/")
