
import os
import numpy as np
import pandas as pd
from scipy import stats

DL = "C:\Users\kraam\Downloads"
FS = os.path.join(DL, "Final Submission", "data")

print("Loading full NPI file...")
df = pd.read_csv(os.path.join(FS, "prescribers_full_npi.csv"))

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

clean = prescriber.dropna(subset=["brand_share", "specialty"]).copy()
clean = clean[clean["total_clms"] >= 20]
print(f"Analyzable prescribers: {len(clean):,}")

spec_volume = clean.groupby("specialty")["total_cost"].sum().sort_values(ascending=False)
top_specs = spec_volume.head(20).index.tolist()
subset = clean[clean["specialty"].isin(top_specs)]
print(f"Top 20 specialties cover {len(subset):,} prescribers")

spec_brand = subset.groupby("specialty").agg(
    n_prescribers=("Prscrbr_NPI", "nunique"),
    mean_brand_share=("brand_share", "mean"),
    median_brand_share=("brand_share", "median"),
    std_brand_share=("brand_share", "std"),
    total_clms=("total_clms", "sum"),
    brand_clms=("brand_clms", "sum"),
    total_cost=("total_cost", "sum"),
    brand_cost=("brand_cost", "sum"),
).reset_index()
spec_brand["weighted_brand_share"] = spec_brand["brand_clms"] / spec_brand["total_clms"]
spec_brand = spec_brand.sort_values("weighted_brand_share", ascending=False)

groups = [subset.loc[subset["specialty"] == s, "brand_share"].values for s in top_specs]
F, p = stats.f_oneway(*groups)
all_vals = np.concatenate(groups)
gm = all_vals.mean()
ss_b = sum(len(g) * (g.mean() - gm) ** 2 for g in groups)
ss_t = np.sum((all_vals - gm) ** 2)
eta = ss_b / ss_t
H, p_kw = stats.kruskal(*groups)
print(f"Specialty ANOVA: F = {F:.2f}, p = {p:.4g}, eta-squared = {eta:.4f}")
print(f"Specialty Kruskal-Wallis: H = {H:.2f}, p = {p_kw:.4g}")

spec_brand.to_csv(os.path.join(FS, "rq3_specialty_brand.csv"), index=False)
pd.DataFrame([
    {"test":"One-way ANOVA","outcome":"prescriber brand_share",
     "grouping":"specialty","k_groups":len(top_specs),"n_total":len(all_vals),
     "F_statistic":F,"df_between":len(top_specs)-1,
     "df_within":len(all_vals)-len(top_specs),"p_value":p,"eta_squared":eta},
    {"test":"Kruskal-Wallis H","outcome":"prescriber brand_share",
     "grouping":"specialty","k_groups":len(top_specs),"n_total":len(all_vals),
     "F_statistic":H,"df_between":len(top_specs)-1,
     "df_within":np.nan,"p_value":p_kw,"eta_squared":np.nan},
]).to_csv(os.path.join(FS, "rq3_anova_results.csv"), index=False)
print("Saved.")
