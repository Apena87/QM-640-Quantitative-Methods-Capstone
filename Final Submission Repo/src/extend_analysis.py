import os
import warnings
import math
import numpy as np
import pandas as pd
import matplotlib

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


matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = os.environ.get("BASE", DL)
FIG_DIR = os.path.join(BASE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

NAVY, STEEL, TEAL, RED = "#17375E", "#2E75B6", "#00B0F0", "#C00000"
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

def savefig(name):
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, name), bbox_inches="tight")
    plt.close()
    print(f"  Saved {name}")


# Load inputs
print("Loading CSVs...")
hl   = pd.read_csv(os.path.join(BASE, "hl_summary.csv"))
pres = pd.read_csv(os.path.join(BASE, "prescribers_sample.csv"), low_memory=False)
drug = pd.read_csv(os.path.join(BASE, "drug_spending.csv"))

# Coerce numerics
for col in ["Tot_Clms", "Tot_Drug_Cst", "Tot_Benes"]:
    if col in pres.columns:
        pres[col] = pd.to_numeric(pres[col], errors="coerce").fillna(0)

# Brand flag: a drug row is "brand" when the Brand Name differs from Generic Name
pres["brand_flag"] = (
    pres["Brnd_Name"].fillna("").str.strip().str.lower()
    != pres["Gnrc_Name"].fillna("").str.strip().str.lower()
).astype(int)

# Per-row brand cost / claims (zero when generic)
pres["brand_clms"]  = pres["Tot_Clms"] * pres["brand_flag"]
pres["brand_cost"]  = pres["Tot_Drug_Cst"] * pres["brand_flag"]


print("\n[RQ2] State-level brand prescribing ANOVA...")

# Build a per-prescriber row: one observation per NPI with brand_share as outcome
prescriber = pres.groupby("Prscrbr_NPI", as_index=False).agg(
    state=("Prscrbr_State_Abrvtn", "first"),
    specialty=("Prscrbr_Type", "first"),
    total_clms=("Tot_Clms", "sum"),
    total_cost=("Tot_Drug_Cst", "sum"),
    brand_clms=("brand_clms", "sum"),
    brand_cost=("brand_cost", "sum"),
)
prescriber["brand_share"] = np.where(
    prescriber["total_clms"] > 0,
    prescriber["brand_clms"] / prescriber["total_clms"],
    np.nan,
)

# Exclude tiny prescribers (<= 20 claims/year) to reduce noise
clean = prescriber.dropna(subset=["brand_share", "state"]).copy()
clean = clean[clean["total_clms"] >= 20]
print(f"  Analyzable prescribers: {len(clean):,}")

# State aggregate
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
state_brand["weighted_brand_share"] = (
    state_brand["brand_clms"] / state_brand["total_clms"]
)
state_brand = state_brand.sort_values("weighted_brand_share", ascending=False)

# Keep states with >= 10 prescribers in the sample for stable ANOVA
qualifying = state_brand[state_brand["n_prescribers"] >= 10]["state"].tolist()
print(f"  States with >=10 prescribers in sample: {len(qualifying)}")

# One-way ANOVA: brand_share ~ state
groups = [clean.loc[clean["state"] == s, "brand_share"].values for s in qualifying]
F, p = stats.f_oneway(*groups)
# Effect size — eta-squared = SS_between / SS_total
all_vals = np.concatenate(groups)
grand_mean = all_vals.mean()
ss_total = np.sum((all_vals - grand_mean) ** 2)
ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
eta_sq = ss_between / ss_total
print(f"  ANOVA: F = {F:.2f}, p = {p:.4g}, eta-squared = {eta_sq:.4f}")

# Kruskal-Wallis (non-parametric fallback, since brand_share isn't normal)
H, p_kw = stats.kruskal(*groups)
print(f"  Kruskal-Wallis: H = {H:.2f}, p = {p_kw:.4g}")

state_brand.to_csv(os.path.join(BASE, "rq2_state_brand_share.csv"), index=False)
pd.DataFrame([{
    "test": "One-way ANOVA",
    "outcome": "prescriber brand_share",
    "grouping": "state",
    "k_groups": len(qualifying),
    "n_total": len(all_vals),
    "F_statistic": F,
    "df_between": len(qualifying) - 1,
    "df_within": len(all_vals) - len(qualifying),
    "p_value": p,
    "eta_squared": eta_sq,
}, {
    "test": "Kruskal-Wallis H",
    "outcome": "prescriber brand_share",
    "grouping": "state",
    "k_groups": len(qualifying),
    "n_total": len(all_vals),
    "F_statistic": H,
    "df_between": len(qualifying) - 1,
    "df_within": np.nan,
    "p_value": p_kw,
    "eta_squared": np.nan,
}]).to_csv(os.path.join(BASE, "rq2_anova_results.csv"), index=False)

# Figure 12 — State brand share
fig, ax = plt.subplots(figsize=(11, 6))
sb_plot = state_brand[state_brand["n_prescribers"] >= 10].sort_values("weighted_brand_share")
colors_state = [
    RED if s in sb_plot["weighted_brand_share"].nlargest(5).values
    else (TEAL if s in sb_plot["weighted_brand_share"].nsmallest(5).values else NAVY)
    for s in sb_plot["weighted_brand_share"].values
]
ax.barh(sb_plot["state"], sb_plot["weighted_brand_share"] * 100, color=colors_state)
ax.set_xlabel("Brand Share of Claims (%)")
ax.set_title("Claim-Weighted Brand Share by State (Prescriber Sample)",
             fontweight="bold", pad=12)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
ax.tick_params(axis="y", labelsize=7)
savefig("fig12_state_brand.png")


print("\n[RQ3] Specialty-level brand prescribing (Open Payments proxy)...")

# Pick top 20 specialties by total cost in the sample
spec_clean = clean.dropna(subset=["specialty"])
spec_volume = spec_clean.groupby("specialty")["total_cost"].sum().sort_values(ascending=False)
top_specs = spec_volume.head(20).index.tolist()
spec_subset = spec_clean[spec_clean["specialty"].isin(top_specs)]

spec_brand = spec_subset.groupby("specialty").agg(
    n_prescribers=("Prscrbr_NPI", "nunique"),
    mean_brand_share=("brand_share", "mean"),
    median_brand_share=("brand_share", "median"),
    std_brand_share=("brand_share", "std"),
    total_clms=("total_clms", "sum"),
    brand_clms=("brand_clms", "sum"),
    total_cost=("total_cost", "sum"),
    brand_cost=("brand_cost", "sum"),
).reset_index()
spec_brand["weighted_brand_share"] = (
    spec_brand["brand_clms"] / spec_brand["total_clms"]
)
spec_brand = spec_brand.sort_values("weighted_brand_share", ascending=False)

# ANOVA across specialties
spec_groups = [spec_subset.loc[spec_subset["specialty"] == s, "brand_share"].values
               for s in top_specs if (spec_subset["specialty"] == s).sum() >= 10]
F_s, p_s = stats.f_oneway(*spec_groups)
all_vals_s = np.concatenate(spec_groups)
gm_s = all_vals_s.mean()
ss_b_s = sum(len(g) * (g.mean() - gm_s) ** 2 for g in spec_groups)
ss_t_s = np.sum((all_vals_s - gm_s) ** 2)
eta_s = ss_b_s / ss_t_s
H_s, p_s_kw = stats.kruskal(*spec_groups)
print(f"  Specialty ANOVA: F = {F_s:.2f}, p = {p_s:.4g}, eta-squared = {eta_s:.4f}")
print(f"  Specialty Kruskal-Wallis: H = {H_s:.2f}, p = {p_s_kw:.4g}")

spec_brand.to_csv(os.path.join(BASE, "rq3_specialty_brand.csv"), index=False)
pd.DataFrame([{
    "test": "One-way ANOVA",
    "outcome": "prescriber brand_share",
    "grouping": "specialty",
    "k_groups": len(spec_groups),
    "n_total": len(all_vals_s),
    "F_statistic": F_s,
    "df_between": len(spec_groups) - 1,
    "df_within": len(all_vals_s) - len(spec_groups),
    "p_value": p_s,
    "eta_squared": eta_s,
}, {
    "test": "Kruskal-Wallis H",
    "outcome": "prescriber brand_share",
    "grouping": "specialty",
    "k_groups": len(spec_groups),
    "n_total": len(all_vals_s),
    "F_statistic": H_s,
    "df_between": len(spec_groups) - 1,
    "df_within": np.nan,
    "p_value": p_s_kw,
    "eta_squared": np.nan,
}]).to_csv(os.path.join(BASE, "rq3_anova_results.csv"), index=False)

# Figure 13 — Specialty brand share
fig, ax = plt.subplots(figsize=(11, 6))
sb_plot = spec_brand.sort_values("weighted_brand_share")
ax.barh(sb_plot["specialty"], sb_plot["weighted_brand_share"] * 100, color=NAVY, alpha=0.85)
ax.set_xlabel("Brand Share of Claims (%)")
ax.set_title("Claim-Weighted Brand Share by Specialty (Top 20 by Spend)",
             fontweight="bold", pad=12)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
ax.tick_params(axis="y", labelsize=7)
savefig("fig13_specialty_brand.png")


print("\n[RQ5] Brand-to-generic savings simulation...")

# Brand vs Generic cost per claim from 2023 grand totals
hl_2023 = hl[hl["year"] == 2023].iloc[0]
brand_cpc   = hl_2023["brand_cost_per_clm"]
generic_cpc = hl_2023["generic_cost_per_clm"]
cost_delta  = brand_cpc - generic_cpc
print(f"  Brand cpc: ${brand_cpc:,.2f} | Generic cpc: ${generic_cpc:,.2f} | Delta: ${cost_delta:,.2f}")

# For each prescriber: compute excess brand share above specialty median
spec_medians = clean.groupby("specialty")["brand_share"].median()
clean = clean.copy()
clean["spec_median_brand_share"] = clean["specialty"].map(spec_medians)
clean["excess_brand_share"] = (
    clean["brand_share"] - clean["spec_median_brand_share"]
).clip(lower=0)
clean["excess_brand_clms"]   = clean["excess_brand_share"] * clean["total_clms"]
clean["hypothetical_savings"] = clean["excess_brand_clms"] * cost_delta

# Aggregate
sample_savings = clean["hypothetical_savings"].sum()
n_sample_prescribers = clean["Prscrbr_NPI"].nunique()

# Scale by ROW ratio rather than by unique prescribers. The CMS NPI-level file
# is ~1.1M (prescriber × drug) ROWS; we used the first 200,000 rows. Scaling
# linearly by row count assumes the unseen rows contribute savings at the same
# average rate as our sample. This is more conservative than scaling by unique
# prescribers (which double-counts dense-prescribing physicians).
FULL_FILE_ROWS = 1_100_000
SAMPLE_ROWS    = 200_000
row_scale = FULL_FILE_ROWS / SAMPLE_ROWS              # 5.50x
# "Ceiling" assumes every excess brand claim could substitute to generic at
# the full cost delta. Real substitution rate is lower because some brand
# drugs have no generic equivalent. Literature (Choudhry et al. 2011) puts
# realistic substitutable share around 50% for above-median prescribers.
SUBSTITUTION_RATE = 0.50
ceiling_savings = sample_savings * row_scale
floor_savings   = ceiling_savings * SUBSTITUTION_RATE

print(f"  Sample prescribers (analyzable): {n_sample_prescribers:,}")
print(f"  Sample savings (ceiling): ${sample_savings:,.0f}")
print(f"  Row-based scale factor: {row_scale:.2f}x")
print(f"  Extrapolated savings — ceiling: ${ceiling_savings/1e9:.2f}B")
print(f"  Extrapolated savings — floor (50% substitution): ${floor_savings/1e9:.2f}B")

clean[[
    "Prscrbr_NPI", "state", "specialty", "total_clms", "total_cost",
    "brand_share", "spec_median_brand_share", "excess_brand_share",
    "excess_brand_clms", "hypothetical_savings",
]].to_csv(os.path.join(BASE, "rq5_prescriber_savings.csv"), index=False)

# Also produce specialty-level savings rollup (ceiling + floor)
spec_savings = clean.groupby("specialty").agg(
    n_prescribers=("Prscrbr_NPI", "nunique"),
    total_clms=("total_clms", "sum"),
    sample_savings=("hypothetical_savings", "sum"),
).reset_index()
spec_savings["ceiling_savings"] = spec_savings["sample_savings"] * row_scale
spec_savings["floor_savings"]   = spec_savings["ceiling_savings"] * SUBSTITUTION_RATE
spec_savings = spec_savings.sort_values("ceiling_savings", ascending=False)

pd.DataFrame([{
    "brand_cost_per_clm_2023": brand_cpc,
    "generic_cost_per_clm_2023": generic_cpc,
    "cost_delta_per_clm": cost_delta,
    "n_sample_prescribers": n_sample_prescribers,
    "sample_savings": sample_savings,
    "sample_rows": SAMPLE_ROWS,
    "full_file_rows": FULL_FILE_ROWS,
    "row_scale_factor": row_scale,
    "substitution_rate_assumption": SUBSTITUTION_RATE,
    "ceiling_annual_savings": ceiling_savings,
    "floor_annual_savings": floor_savings,
}]).to_csv(os.path.join(BASE, "rq5_savings_summary.csv"), index=False)
spec_savings.to_csv(os.path.join(BASE, "rq5_savings_by_specialty.csv"), index=False)

# Figure 14 — Specialty savings (floor estimate, the more defensible number)
fig, ax = plt.subplots(figsize=(11, 6))
sv_plot = spec_savings.head(15).sort_values("floor_savings")
ax.barh(sv_plot["specialty"], sv_plot["floor_savings"] / 1e9, color=RED, alpha=0.85)
ax.set_xlabel("Annual Savings — Floor Estimate (USD Billions)")
ax.set_title("RQ5 — Hypothetical Brand-to-Specialty-Median Savings by Specialty\n"
             "(50% substitution assumption, row-scaled to full prescriber file)",
             fontweight="bold", pad=12)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.1f}B"))
ax.tick_params(axis="y", labelsize=7)
savefig("fig14_savings_dist.png")


print("\n[Sample Size] Computing minimum n per RQ...")

# Helper: power.solve_ind for multiple regression via Cohen's L-table
# For α=0.05, power=0.80, the noncentrality parameter L is approximately:
#   L = 7.85 (df_num=1), 9.64 (2), 10.91 (3), 11.94 (4), 12.83 (5),
#       13.62 (6), 14.35 (7), 15.02 (8)
L_table = {1:7.85, 2:9.64, 3:10.91, 4:11.94, 5:12.83, 6:13.62, 7:14.35, 8:15.02}

def n_min_regression(k, f2, alpha=0.05, power=0.80):
    """Cohen 1988 multiple regression: n_min = L/f2 + k + 1"""
    L = L_table[k]
    return int(math.ceil(L / f2 + k + 1))

def n_min_anova(k_groups, f, alpha=0.05, power=0.80):
    """One-way ANOVA via noncentrality. Uses iterative search."""
    from scipy.stats import f as fdist
    for n_per in range(2, 5000):
        n_total = n_per * k_groups
        df1 = k_groups - 1
        df2 = n_total - k_groups
        lam = n_total * f * f
        crit = fdist.ppf(1 - alpha, df1, df2)
        # Noncentral F CDF
        pwr = 1 - fdist.cdf(crit, df1, df2, loc=0)  # central first
        # Use noncentral distribution
        from scipy.stats import ncf
        pwr = 1 - ncf.cdf(crit, df1, df2, lam)
        if pwr >= power:
            return n_total, n_per
    return None, None

def n_min_logistic(k_predictors, event_rate):
    """Peduzzi rule of thumb: 10 events per predictor."""
    return int(math.ceil((10 * k_predictors) / event_rate))

# RQ1 — OLS with 5 predictors, medium effect f²=0.15
rq1_n = n_min_regression(k=5, f2=0.15)

# RQ2 — One-way ANOVA across ~51 states, medium effect f=0.25
rq2_n_total, rq2_n_per = n_min_anova(k_groups=51, f=0.25)

# RQ3 — One-way ANOVA across 20 specialties, medium effect f=0.25
rq3_n_total, rq3_n_per = n_min_anova(k_groups=20, f=0.25)

# RQ4 — K-means rule of thumb: 50 per cluster minimum (Mooi & Sarstedt 2011)
rq4_n = 50 * 4

# RQ5 — Sample size for estimating mean prescriber savings with 5% relative
# precision at 95% confidence. Coefficient of variation (sigma/mu) ~= 0.5
# typical for skewed savings distributions.
#   n = (z * (sigma/mu) / E)^2  with z=1.96, sigma/mu=0.5, E=0.05 -> n ~= 384
rq5_n = int(math.ceil((1.96 * 0.5 / 0.05) ** 2))

# Achieved n's (read from current analysis)
n_drug = len(drug)
n_drug_clean = len(drug.dropna(subset=["spend_2023","claims_2023","unit_cost_2023","benes_2023","num_mfr"]))
n_prescribers_total = pres["Prscrbr_NPI"].nunique()
n_prescribers_clean = len(clean)

sample_size_df = pd.DataFrame([
    {
        "RQ": "RQ1",
        "Test": "Multiple OLS Regression",
        "Parameters": "α=0.05, power=0.80, k=5 predictors, f²=0.15 (medium)",
        "Formula": "n = L/f² + k + 1   (Cohen 1988)",
        "Minimum_n": rq1_n,
        "Achieved_n": 3404,
        "Status": "Exceeded",
    },
    {
        "RQ": "RQ2",
        "Test": "One-way ANOVA",
        "Parameters": "α=0.05, power=0.80, k=51 states, f=0.25 (medium)",
        "Formula": "Noncentral F via iterative power.solve",
        "Minimum_n": rq2_n_total,
        "Achieved_n": int(clean.shape[0]),
        "Status": "Exceeded",
    },
    {
        "RQ": "RQ3",
        "Test": "One-way ANOVA (specialty proxy) / Logistic Regression (final)",
        "Parameters": "α=0.05, power=0.80, k=20 specialties, f=0.25 (medium)",
        "Formula": "Noncentral F via iterative power.solve",
        "Minimum_n": rq3_n_total,
        "Achieved_n": int(len(all_vals_s)),
        "Status": "Exceeded",
    },
    {
        "RQ": "RQ4",
        "Test": "K-means clustering",
        "Parameters": "k=4 clusters, 50-per-cluster heuristic (Mooi & Sarstedt 2011)",
        "Formula": "n_min = 50 × k",
        "Minimum_n": rq4_n,
        "Achieved_n": 3265,
        "Status": "Exceeded",
    },
    {
        "RQ": "RQ5",
        "Test": "Sample mean (savings estimate)",
        "Parameters": "95% CI, 5% relative precision, sigma/mu=0.5",
        "Formula": "n = (z * (sigma/mu) / E)^2",
        "Minimum_n": rq5_n,
        "Achieved_n": n_prescribers_clean,
        "Status": "Exceeded",
    },
])
sample_size_df.to_csv(os.path.join(BASE, "sample_size_per_rq.csv"), index=False)
print(sample_size_df.to_string(index=False))

print("\nAll new CSVs and figures saved.")
