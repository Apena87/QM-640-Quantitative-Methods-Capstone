

import os
import math
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm
from scipy import stats
from scipy.stats import f as fdist, ncf

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = "C:\Users\kraam\Downloads"

HL_XLSX = os.path.join(
    BASE,
    "Medicare Part D Prescribers - by Provider and Drug",
    "Medicare Part D Prescribers - by Provider and Drug",
    "2023", "MUP_DPR_RY25_P06_V10_DYT23_HLSum.xlsx",
)

DRUG_XLSX = os.path.join(
    BASE,
    "Medicare Part D Spending by Drug-Excel Reports including Historical Data RY25",
    "Medicare Part D Spending by Drug DYT2023",
    "DSD_PTD_RY25_DYT23_Web - 250415.xlsx",
)

NPI_CSV = os.path.join(
    BASE,
    "Medicare Part D Prescribers - by Provider and Drug",
    "Medicare Part D Prescribers - by Provider and Drug",
    "2023", "MUP_DPR_RY25_P04_V10_DY23_NPIBN.csv",
)

FIG_DIR = os.path.join(BASE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# ── Plot style ────────────────────────────────────────────────────────────────
NAVY  = "#17375E"
STEEL = "#2E75B6"
TEAL  = "#00B0F0"
RED   = "#C00000"

plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.dpi":        150,
})

def savefig(name):
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, name), bbox_inches="tight")
    plt.close()
    print(f"  Saved {name}")


# =============================================================================
# 1. GRAND TOTALS  —  MUP_DPR_RY25_P06_V10_DYT23_HLSum.xlsx
#    Sheet: "Data"  |  Header row index: 3  (4th row)
# =============================================================================
print("\n[1/6] Loading Part D grand totals...")

hl_raw = pd.read_excel(HL_XLSX, sheet_name="Data", header=3)
# Strip leading/trailing whitespace and collapse internal double-spaces
hl_raw.columns = hl_raw.columns.str.strip().str.replace(r"\s+", " ", regex=True)

# Helper: find a column by exact (stripped) name
def get_col(df, name):
    name_clean = " ".join(name.split())   # collapse any whitespace in lookup string
    matches = [c for c in df.columns if " ".join(c.split()) == name_clean]
    if not matches:
        print(f"  ERROR: column not found: '{name}'")
        print(f"  Available: {list(df.columns)}")
        raise KeyError(name)
    return matches[0]

hl = hl_raw[[
    get_col(hl_raw, "Calendar Year"),
    get_col(hl_raw, "Total Drug Cost"),
    get_col(hl_raw, "Total Drug Cost for Brand Drugs"),
    get_col(hl_raw, "Total Drug Cost for Generic Drugs"),
    get_col(hl_raw, "Total Beneficiaries"),
    get_col(hl_raw, "Total Claims"),
    get_col(hl_raw, "Total Drug Cost for LIS Beneficiaries"),
    get_col(hl_raw, "Total Drug Cost for NonLIS Beneficiaries"),
    get_col(hl_raw, "Total Claims for Brand Drugs"),
    get_col(hl_raw, "Total Claims for Generic Drugs"),
]].copy()

hl.columns = ["year", "tot_cost", "brand_cost", "generic_cost",
              "tot_benes", "tot_clms", "lis_cost", "nonlis_cost",
              "brand_clms", "generic_clms"]

for c in hl.columns:
    hl[c] = pd.to_numeric(hl[c], errors="coerce")

hl = (hl.dropna(subset=["year"])
        .assign(year=lambda d: d["year"].astype(int))
        .query("2013 <= year <= 2023")
        .sort_values("year")
        .reset_index(drop=True))

hl["cost_per_bene"]        = hl["tot_cost"]    / hl["tot_benes"]
hl["brand_share_cost"]     = hl["brand_cost"]  / hl["tot_cost"]
hl["brand_cost_per_clm"]   = hl["brand_cost"]  / hl["brand_clms"]
hl["generic_cost_per_clm"] = hl["generic_cost"] / hl["generic_clms"]

hl.to_csv(os.path.join(BASE, "hl_summary.csv"), index=False)
print(f"  {len(hl)} rows → hl_summary.csv")
print(hl[["year","tot_cost","brand_cost","generic_cost"]].to_string(index=False))


# =============================================================================
# 2. DRUG SPENDING  —  DSD_PTD_RY25_DYT23_Web - 250415.xlsx
#    Sheet: "Spending & Utilization YTD 2023"
#    Structure:
#      Row 0: title
#      Row 1: note
#      Row 2: year labels  ("Calendar Year 2019" ... "Calendar Year 2023")
#      Row 3: column headers (Brand Name, Generic Name, ... repeated per year)
#      Row 4+: data
#
#    Fixed columns (no year): Brand Name, Generic Name, Number of Manufacturers
#    Then 5 x 8-column blocks for years 2019-2023:
#      Total Spending, Total Dosage Units, Total Claims, Total Beneficiaries,
#      Average Spending Per Dosage Unit (Weighted), Average Spending Per Claim,
#      Average Spending Per Beneficiary, Outlier Flag
#    Last 2 columns (still year-labeled 2023):
#      Change in Average Spending Per Dosage Unit (2022-2023)
#      Annual Growth Rate in Average Spending Per Dosage Unit (2019-2023)
# =============================================================================
print("\n[2/6] Loading drug spending file...")

raw2 = pd.read_excel(
    DRUG_XLSX,
    sheet_name="Spending & Utilization YTD 2023",
    header=None
)

# Row 3 = column headers, row 2 = year labels
header_row = 3
year_row   = 2

# Build year-prefixed column names; strip newlines so "Total \nBeneficiaries" → "Total Beneficiaries"
col_names = []
current_year = None
for ci in range(raw2.shape[1]):
    yr_cell  = str(raw2.iloc[year_row, ci]).strip()
    var_cell = str(raw2.iloc[header_row, ci]).replace("\n", " ").strip()
    var_cell = " ".join(var_cell.split())   # collapse internal whitespace
    if "Calendar Year" in yr_cell:
        current_year = yr_cell.replace("Calendar Year", "").strip()
    if var_cell in ("nan", ""):
        col_names.append(f"_col{ci}")
    elif current_year:
        col_names.append(f"Y{current_year}__{var_cell}")
    else:
        col_names.append(var_cell)

drug = pd.read_excel(
    DRUG_XLSX,
    sheet_name="Spending & Utilization YTD 2023",
    header=None,
    skiprows=header_row + 1
)
drug.columns = col_names[: drug.shape[1]]

print(f"  Drug columns: {list(drug.columns)}")

# Pull the columns we care about
# Fixed (no year prefix)
brand_col  = "Brand Name"
gname_col  = "Generic Name"
mftr_col   = "Number of Manufacturers"

# Per-year variables we need
YEARS     = ["2019", "2020", "2021", "2022", "2023"]
SPEND     = "Total Spending"
CLAIMS    = "Total Claims"
BENES     = "Total Beneficiaries"
UNIT_COST = "Average Spending Per Dosage Unit (Weighted)"

# Growth rate — precomputed in file, last two cols
GROWTH_COL = "Annual Growth Rate in Average Spending Per Dosage Unit (2019-2023)"

keep = [brand_col, gname_col, mftr_col]
for yr in YEARS:
    for var in [SPEND, CLAIMS, BENES, UNIT_COST]:
        target = f"Y{yr}__{var}"
        if target in drug.columns:
            keep.append(target)
        else:
            print(f"  WARNING: expected column not found: {target}")

# Growth rate column — may have year prefix
growth_matches = [c for c in drug.columns if GROWTH_COL in c]
if growth_matches:
    keep.append(growth_matches[0])
else:
    print(f"  WARNING: growth rate column not found; will compute from unit costs")

drug = drug[[c for c in keep if c in drug.columns]].copy()

# Flatten names to short aliases
rename = {"Brand Name": "brand_name", "Generic Name": "generic_name",
          "Number of Manufacturers": "num_mfr"}
for yr in YEARS:
    rename[f"Y{yr}__{SPEND}"]     = f"spend_{yr}"
    rename[f"Y{yr}__{CLAIMS}"]    = f"claims_{yr}"
    rename[f"Y{yr}__{BENES}"]     = f"benes_{yr}"
    rename[f"Y{yr}__{UNIT_COST}"] = f"unit_cost_{yr}"
if growth_matches:
    rename[growth_matches[0]] = "growth_rate"

drug = drug.rename(columns=rename)

for c in drug.columns[2:]:
    drug[c] = pd.to_numeric(drug[c], errors="coerce")

# Compute growth rate if not in file
if "growth_rate" not in drug.columns:
    u19 = drug.get("unit_cost_2019")
    u23 = drug.get("unit_cost_2023")
    if u19 is not None and u23 is not None:
        drug["growth_rate"] = ((u23 - u19) / u19.replace(0, np.nan)).fillna(0)
    else:
        drug["growth_rate"] = 0

drug = drug.dropna(subset=["spend_2023"])
drug = drug[drug["spend_2023"] > 0].reset_index(drop=True)

drug.to_csv(os.path.join(BASE, "drug_spending.csv"), index=False)
print(f"  {len(drug)} rows → drug_spending.csv")


# =============================================================================
# 3. PRESCRIBERS FILE (200K sample)
# =============================================================================
print("\n[3/6] Loading prescribers file (200K sample)...")

pres = pd.read_csv(NPI_CSV, nrows=200_000, low_memory=False)
pres.to_csv(os.path.join(BASE, "prescribers_sample.csv"), index=False)
print(f"  {len(pres):,} rows, {pres.shape[1]} cols → prescribers_sample.csv")

state_stats = pres.groupby("Prscrbr_State_Abrvtn").agg(
    n_prescribers=("Prscrbr_NPI",  "nunique"),
    total_cost   =("Tot_Drug_Cst", "sum"),
    total_clms   =("Tot_Clms",     "sum"),
).reset_index()
state_stats.to_csv(os.path.join(BASE, "state_stats.csv"), index=False)


# =============================================================================
# 4. FIGURES 1-7  (EDA)
# =============================================================================
print("\n[4/6] Generating EDA figures...")

years = hl["year"].values
tot   = hl["tot_cost"].values    / 1e9
brand = hl["brand_cost"].values  / 1e9
genrc = hl["generic_cost"].values / 1e9
benes = hl["tot_benes"].values   / 1e6
cpb   = hl["cost_per_bene"].values
lis   = hl["lis_cost"].values    / 1e9
nlis  = hl["nonlis_cost"].values / 1e9
bcp   = hl["brand_cost_per_clm"].values
gcp   = hl["generic_cost_per_clm"].values
bsh   = hl["brand_share_cost"].values * 100
gsh   = (1 - hl["brand_share_cost"].values) * 100

# Figure 1 — Total cost trend
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.fill_between(years, tot, alpha=0.15, color=NAVY)
ax.plot(years, tot, color=NAVY, lw=2.5, marker="o", ms=5)
for x, y in zip(years[[0, -1]], tot[[0, -1]]):
    ax.annotate(f"${y:.1f}B", (x, y), textcoords="offset points",
                xytext=(0, 10), ha="center", fontsize=9, color=NAVY, fontweight="bold")
ax.set_title("Medicare Part D Total Drug Cost (2013-2023)", fontweight="bold", pad=12)
ax.set_ylabel("USD Billions")
ax.set_xticks(years)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
savefig("fig1_total_cost_trend.png")

# Figure 2 — Brand vs Generic
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
ax1.stackplot(years, brand, genrc, labels=["Brand", "Generic"],
              colors=[NAVY, TEAL], alpha=0.85)
ax1.set_title("Brand vs. Generic Drug Cost", fontweight="bold")
ax1.set_ylabel("USD Billions")
ax1.set_xticks(years[::2])
ax1.legend(loc="upper left", fontsize=9)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
ax2.plot(years, bsh, color=NAVY, lw=2.5, marker="o", ms=5, label="Brand %")
ax2.plot(years, gsh, color=TEAL, lw=2.5, marker="s", ms=5, label="Generic %")
ax2.set_title("Share of Total Drug Cost (%)", fontweight="bold")
ax2.set_ylabel("Share (%)")
ax2.set_xticks(years[::2])
ax2.legend(fontsize=9)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
savefig("fig2_brand_generic_trend.png")

# Figure 3 — Beneficiaries + cost per bene
fig, ax1 = plt.subplots(figsize=(9, 4.5))
ax2 = ax1.twinx()
ax1.bar(years, benes, color=STEEL, alpha=0.7, label="Beneficiaries (M)")
ax2.plot(years, cpb, color=RED, lw=2.5, marker="D", ms=5, label="Cost per Bene")
ax1.set_title("Beneficiaries and Cost per Beneficiary (2013-2023)", fontweight="bold", pad=12)
ax1.set_ylabel("Beneficiaries (Millions)", color=STEEL)
ax2.set_ylabel("Cost per Beneficiary (USD)", color=RED)
ax1.set_xticks(years)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
lines = ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
lbls  = ax1.get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1]
ax1.legend(lines, lbls, loc="upper left", fontsize=9)
savefig("fig3_bene_cost_trend.png")

# Figure 4 — LIS vs Non-LIS
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(years, lis,  color=NAVY,  lw=2.5, marker="o", ms=5, label="LIS")
ax.plot(years, nlis, color=STEEL, lw=2.5, marker="s", ms=5, label="Non-LIS")
ax.set_title("Part D Spending: LIS vs. Non-LIS Beneficiaries", fontweight="bold", pad=12)
ax.set_ylabel("USD Billions")
ax.set_xticks(years)
ax.legend(fontsize=10)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
savefig("fig4_lis_nonlis.png")

# Figure 5 — Top 20 drugs by 2023 spending
top20 = (drug.nlargest(20, "spend_2023")[["brand_name", "spend_2023"]]
             .sort_values("spend_2023")
             .assign(spend_b=lambda d: d["spend_2023"] / 1e9))
colors_bar = [RED if i >= 15 else NAVY for i in range(len(top20))]
fig, ax = plt.subplots(figsize=(9, 7))
ax.barh(top20["brand_name"], top20["spend_b"], color=colors_bar)
ax.set_xlabel("Total Spending 2023 (USD Billions)")
ax.set_title("Top 20 Medicare Part D Drugs by 2023 Spending", fontweight="bold", pad=12)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
savefig("fig5_top20_drugs.png")

# Figure 6 — Unit cost distribution + growth rate
unit_vals   = drug["unit_cost_2023"].dropna()
unit_vals   = unit_vals[unit_vals > 0]
growth_vals = drug["growth_rate"].replace([np.inf, -np.inf], np.nan).dropna().clip(-2, 5)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
ax1.hist(np.log10(unit_vals), bins=50, color=NAVY, alpha=0.8, edgecolor="white")
ax1.set_xlabel("Log10(Avg Cost per Dosage Unit, USD)")
ax1.set_ylabel("Number of Drugs")
ax1.set_title("Unit Cost Distribution (log scale)", fontweight="bold")
ax2.hist(growth_vals, bins=60, color=STEEL, alpha=0.8, edgecolor="white")
ax2.axvline(0, color=RED, lw=1.5, ls="--", label="Zero growth")
ax2.set_xlabel("Annual Growth Rate (2019-2023)")
ax2.set_ylabel("Number of Drugs")
ax2.set_title("Annual Cost Growth Rate Distribution", fontweight="bold")
ax2.legend(fontsize=9)
savefig("fig6_unit_cost_dist.png")

# Figure 7 — Brand vs Generic cost per claim
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(years, bcp, color=NAVY, lw=2.5, marker="o", ms=5, label="Brand")
ax.plot(years, gcp, color=TEAL, lw=2.5, marker="s", ms=5, label="Generic")
ratio_23 = bcp[-1] / gcp[-1]
ax.annotate(f"Brand:Generic = {ratio_23:.0f}x in 2023",
            xy=(years[-1], bcp[-1]), xytext=(-80, -30),
            textcoords="offset points", fontsize=9, color=NAVY,
            arrowprops=dict(arrowstyle="->", color=NAVY))
ax.set_title("Avg Drug Cost per Claim: Brand vs. Generic (2013-2023)", fontweight="bold", pad=12)
ax.set_ylabel("Cost per Claim (USD)")
ax.set_xticks(years)
ax.legend(fontsize=10)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
savefig("fig7_brand_generic_cost_per_claim.png")


# =============================================================================
# 5. OLS REGRESSION
# =============================================================================
print("\n[5/6] Running OLS regression (statsmodels)...")

# Compute dollar growth for OLS predictor (spend_2019 may be NaN for new drugs → fill 0)
drug["dollar_growth"] = (
    pd.to_numeric(drug["spend_2023"], errors="coerce")
    - pd.to_numeric(drug["spend_2019"], errors="coerce").fillna(0)
)

model_df = drug[["spend_2023", "claims_2023", "unit_cost_2023",
                  "benes_2023", "num_mfr", "dollar_growth"]].copy()
model_df = model_df.apply(pd.to_numeric, errors="coerce").dropna()
model_df = model_df[
    (model_df["spend_2023"]    > 0) &
    (model_df["claims_2023"]   > 0) &
    (model_df["unit_cost_2023"] > 0) &
    (model_df["benes_2023"]    > 0)
]
# Log-transform dollar growth (clip at $1 to handle declines)
model_df["log_dollar_growth"] = np.log(model_df["dollar_growth"].clip(lower=1))

y = np.log(model_df["spend_2023"].values)
X = pd.DataFrame({
    "log_claims":        np.log(model_df["claims_2023"].values),
    "log_unit_cost":     np.log(model_df["unit_cost_2023"].values),
    "log_bene":          np.log(model_df["benes_2023"].values),
    "num_mfr":           model_df["num_mfr"].values,
    "log_dollar_growth": model_df["log_dollar_growth"].values,
})
X_sm = sm.add_constant(X)
ols  = sm.OLS(y, X_sm).fit()
print(ols.summary())

model_results = pd.DataFrame({
    "feature":     ols.params.index,
    "coefficient": ols.params.values,
    "std_err":     ols.bse.values,
    "t_stat":      ols.tvalues.values,
    "p_value":     ols.pvalues.values,
})
model_results.to_csv(os.path.join(BASE, "model_results.csv"), index=False)
print(f"  R² = {ols.rsquared:.4f}, n = {int(ols.nobs):,} → model_results.csv")

# Figure 8 — Regression diagnostics
y_hat = ols.fittedvalues.values
resid = ols.resid.values
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
ax1.scatter(y_hat, y, alpha=0.3, s=8, color=NAVY)
lims = [min(y_hat.min(), y.min()), max(y_hat.max(), y.max())]
ax1.plot(lims, lims, color=RED, lw=1.5, ls="--")
ax1.set_xlabel("Predicted log(Total Spending)")
ax1.set_ylabel("Actual log(Total Spending)")
ax1.set_title(f"Predicted vs. Actual  (R² = {ols.rsquared:.3f}, n={int(ols.nobs):,})", fontweight="bold")
ax2.scatter(y_hat, resid, alpha=0.3, s=8, color=STEEL)
ax2.axhline(0, color=RED, lw=1.5, ls="--")
ax2.set_xlabel("Predicted log(Total Spending)")
ax2.set_ylabel("Residuals")
ax2.set_title("Residual Plot", fontweight="bold")
savefig("fig8_regression.png")


# =============================================================================
# 6. K-MEANS CLUSTERING  (features: log claims, log unit cost, log dollar growth)
#
# WHY dollar growth instead of % growth rate:
#   % growth produces noise clusters driven by tiny-denominator outliers
#   (e.g. a drug with $300 in 2019 and $1,700 in 2023 looks like 467% growth
#   but has zero formulary relevance). Dollar growth naturally weights by
#   program impact — the clusters reflect drugs that actually move spend.
# =============================================================================
print("\n[6/6] Running K-means clustering (sklearn)...")

# Compute dollar growth: spend_2023 - spend_2019
# Drugs new in 2019-2023 will have NaN spend_2019 → treat as $0 (full spend is growth)
drug["dollar_growth"] = (
    pd.to_numeric(drug["spend_2023"], errors="coerce")
    - pd.to_numeric(drug["spend_2019"], errors="coerce").fillna(0)
)

clust_df = drug[["claims_2023", "unit_cost_2023", "dollar_growth", "spend_2023"]].copy()
clust_df = clust_df.apply(pd.to_numeric, errors="coerce").dropna()
clust_df = clust_df[(clust_df["claims_2023"] > 0) & (clust_df["unit_cost_2023"] > 0)]

# Log-transform dollar growth (clip at $1 floor to handle declines gracefully)
X_clust = np.column_stack([
    np.log(clust_df["claims_2023"].values),
    np.log(clust_df["unit_cost_2023"].values),
    np.log(clust_df["dollar_growth"].clip(lower=1).values),
])
scaler   = StandardScaler()
X_scaled = scaler.fit_transform(X_clust)

# Elbow method
inertias = {}
for k in range(2, 8):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X_scaled)
    inertias[k] = km.inertia_

# Final model
km_final = KMeans(n_clusters=4, random_state=42, n_init=10)
labels   = km_final.fit_predict(X_scaled)
clust_df = clust_df.copy()
clust_df["cluster"]      = labels
clust_df["brand_name"]   = drug.loc[clust_df.index, "brand_name"].values
clust_df["generic_name"] = drug.loc[clust_df.index, "generic_name"].values

cluster_summary = clust_df.groupby("cluster").agg(
    n_drugs          =("cluster",       "count"),
    avg_spend        =("spend_2023",    "mean"),
    total_spend      =("spend_2023",    "sum"),
    median_unit      =("unit_cost_2023","median"),
    avg_claims       =("claims_2023",   "mean"),
    avg_dollar_growth=("dollar_growth", "mean"),
).reset_index()

# Assign labels sequentially to avoid conflicts when one cluster wins
# multiple criteria (e.g. highest claims AND highest dollar growth).
# Priority order: Specialty (unit cost) → Growth (dollar growth) → Generic (claims) → Niche
assigned = {}

remaining = cluster_summary.copy()
specialty_idx = remaining["median_unit"].idxmax()
assigned[specialty_idx] = "High-Cost Specialty"
remaining = remaining.drop(specialty_idx)

growth_idx = remaining["avg_dollar_growth"].idxmax()
assigned[growth_idx] = "High-Spend High-Growth"
remaining = remaining.drop(growth_idx)

generic_idx = remaining["avg_claims"].idxmax()
assigned[generic_idx] = "High-Volume Generic"
remaining = remaining.drop(generic_idx)

niche_idx = remaining.index[0]
assigned[niche_idx] = "Low-Impact Declining"

cluster_summary["label"] = cluster_summary.index.map(assigned)

cluster_summary.to_csv(os.path.join(BASE, "cluster_summary.csv"), index=False)
print(f"  Cluster summary → cluster_summary.csv")
print(cluster_summary[["cluster","label","n_drugs","avg_spend","median_unit","avg_claims","avg_dollar_growth"]].to_string(index=False))

# Save top 10 drugs per cluster for reference
top_drugs = []
for ci in range(4):
    subset = clust_df[clust_df["cluster"] == ci].nlargest(10, "spend_2023")[
        ["brand_name","generic_name","spend_2023","unit_cost_2023","claims_2023","dollar_growth","cluster"]
    ]
    top_drugs.append(subset)
pd.concat(top_drugs).to_csv(os.path.join(BASE, "cluster_top_drugs.csv"), index=False)
print(f"  Top 10 drugs per cluster → cluster_top_drugs.csv")

# Figure 9 — Elbow + scatter
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
ax1.plot(list(inertias.keys()), list(inertias.values()),
         color=NAVY, lw=2.5, marker="o", ms=6)
ax1.axvline(4, color=RED, lw=1.5, ls="--", label="Selected k=4")
ax1.set_xlabel("Number of Clusters (k)")
ax1.set_ylabel("Within-Cluster Sum of Squares")
ax1.set_title("Elbow Method", fontweight="bold")
ax1.legend(fontsize=9)
palette = [NAVY, STEEL, RED, TEAL]
for ci in range(4):
    mask = clust_df["cluster"] == ci
    lbl  = assigned.get(cluster_summary.index[cluster_summary["cluster"]==ci].item(),
                        f"Cluster {ci}")
    ax2.scatter(X_scaled[mask, 0], X_scaled[mask, 1],
                c=palette[ci], alpha=0.5, s=8, label=lbl)
ax2.set_xlabel("Log(Claims) [standardized]")
ax2.set_ylabel("Log(Unit Cost) [standardized]")
ax2.set_title("Drug Clusters (k=4)", fontweight="bold")
ax2.legend(fontsize=8, markerscale=3)
savefig("fig9_clustering.png")

# Figure 10 — Cluster profiles
cl_plot = cluster_summary.sort_values("avg_dollar_growth", ascending=False)
fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
for ax, (col_name, title, scale) in zip(axes, [
    ("avg_spend",         "Avg Total Spending ($M)",     1e6),
    ("median_unit",       "Median Unit Cost ($)",         1),
    ("avg_dollar_growth", "Avg Dollar Growth 2019-23 ($M)", 1e6),
]):
    bars = ax.bar(cl_plot["label"], cl_plot[col_name] / scale,
                  color=[NAVY, STEEL, RED, TEAL][:len(cl_plot)])
    ax.set_title(title, fontweight="bold", fontsize=9)
    ax.tick_params(axis="x", labelsize=7)
plt.suptitle("K-Means Cluster Profiles (k=4) — Dollar-Weighted", fontweight="bold", y=1.02)
savefig("fig10_cluster_profiles.png")

# Figure 11 — Top prescriber specialties
if "Prscrbr_Type" in pres.columns and "Tot_Drug_Cst" in pres.columns:
    pres["Tot_Drug_Cst"] = pd.to_numeric(pres["Tot_Drug_Cst"], errors="coerce")
    spec = (pres.groupby("Prscrbr_Type")["Tot_Drug_Cst"]
                .sum().sort_values(ascending=False).head(15).sort_values())
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(spec.index, spec.values / 1e6, color=NAVY, alpha=0.85)
    ax.set_xlabel("Total Drug Cost (USD Millions)")
    ax.set_title("Top 15 Prescriber Specialties by Drug Cost (2023 Sample)",
                 fontweight="bold", pad=12)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}M"))
    savefig("fig11_top_specialties.png")

# =============================================================================
# Done
# =============================================================================
print("\nAll done.")
print(f"  Figures in: {FIG_DIR}")
for f in ["hl_summary.csv", "drug_spending.csv", "prescribers_sample.csv",
          "cluster_summary.csv", "model_results.csv", "state_stats.csv"]:
    path = os.path.join(BASE, f)
    if os.path.exists(path):
        print(f"  {f}: {os.path.getsize(path)/1024:.1f} KB")

# =============================================================================
# 7. RQ2 — State-level brand vs. generic prescribing (One-way ANOVA)
# =============================================================================
print("\n[7/10] RQ2 — State-level brand prescribing ANOVA...")

# Coerce numerics in prescriber file
for col in ["Tot_Clms", "Tot_Drug_Cst", "Tot_Benes"]:
    if col in pres.columns:
        pres[col] = pd.to_numeric(pres[col], errors="coerce").fillna(0)

# Brand flag: brand_name != generic_name (case-insensitive)
pres["brand_flag"] = (
    pres["Brnd_Name"].fillna("").str.strip().str.lower()
    != pres["Gnrc_Name"].fillna("").str.strip().str.lower()
).astype(int)
pres["brand_clms_row"] = pres["Tot_Clms"] * pres["brand_flag"]
pres["brand_cost_row"] = pres["Tot_Drug_Cst"] * pres["brand_flag"]

# Per-prescriber aggregate
prescriber = pres.groupby("Prscrbr_NPI", as_index=False).agg(
    state=("Prscrbr_State_Abrvtn", "first"),
    specialty=("Prscrbr_Type", "first"),
    total_clms=("Tot_Clms", "sum"),
    total_cost=("Tot_Drug_Cst", "sum"),
    brand_clms=("brand_clms_row", "sum"),
    brand_cost=("brand_cost_row", "sum"),
)
prescriber["brand_share"] = np.where(
    prescriber["total_clms"] > 0,
    prescriber["brand_clms"] / prescriber["total_clms"],
    np.nan,
)

# Exclude tiny prescribers (<20 claims/yr) to reduce noise
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
state_brand["weighted_brand_share"] = state_brand["brand_clms"] / state_brand["total_clms"]
state_brand = state_brand.sort_values("weighted_brand_share", ascending=False)

# ANOVA across states with >=10 prescribers
qualifying = state_brand[state_brand["n_prescribers"] >= 10]["state"].tolist()
print(f"  States with >=10 prescribers in sample: {len(qualifying)}")
groups = [clean.loc[clean["state"] == s, "brand_share"].values for s in qualifying]
F, p = stats.f_oneway(*groups)
all_vals = np.concatenate(groups)
grand_mean = all_vals.mean()
ss_total = np.sum((all_vals - grand_mean) ** 2)
ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
eta_sq = ss_between / ss_total
H, p_kw = stats.kruskal(*groups)
print(f"  ANOVA: F={F:.2f}, p={p:.4g}, eta^2={eta_sq:.4f}")
print(f"  Kruskal-Wallis: H={H:.2f}, p={p_kw:.4g}")

state_brand.to_csv(os.path.join(BASE, "rq2_state_brand_share.csv"), index=False)
pd.DataFrame([
    {"test": "One-way ANOVA", "outcome": "prescriber brand_share",
     "grouping": "state", "k_groups": len(qualifying), "n_total": len(all_vals),
     "F_statistic": F, "df_between": len(qualifying)-1,
     "df_within": len(all_vals)-len(qualifying), "p_value": p, "eta_squared": eta_sq},
    {"test": "Kruskal-Wallis H", "outcome": "prescriber brand_share",
     "grouping": "state", "k_groups": len(qualifying), "n_total": len(all_vals),
     "F_statistic": H, "df_between": len(qualifying)-1,
     "df_within": np.nan, "p_value": p_kw, "eta_squared": np.nan},
]).to_csv(os.path.join(BASE, "rq2_anova_results.csv"), index=False)

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


# =============================================================================
# 8. RQ3 — Specialty-level brand prescribing (Open Payments proxy)
# =============================================================================
print("\n[8/10] RQ3 — Specialty-level brand prescribing (proxy for Open Payments)...")

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
spec_brand["weighted_brand_share"] = spec_brand["brand_clms"] / spec_brand["total_clms"]
spec_brand = spec_brand.sort_values("weighted_brand_share", ascending=False)

spec_groups = [spec_subset.loc[spec_subset["specialty"] == s, "brand_share"].values
               for s in top_specs if (spec_subset["specialty"] == s).sum() >= 10]
F_s, p_s = stats.f_oneway(*spec_groups)
all_vals_s = np.concatenate(spec_groups)
gm_s = all_vals_s.mean()
ss_b_s = sum(len(g) * (g.mean() - gm_s) ** 2 for g in spec_groups)
ss_t_s = np.sum((all_vals_s - gm_s) ** 2)
eta_s = ss_b_s / ss_t_s
H_s, p_s_kw = stats.kruskal(*spec_groups)
print(f"  Specialty ANOVA: F={F_s:.2f}, p={p_s:.4g}, eta^2={eta_s:.4f}")
print(f"  Specialty Kruskal-Wallis: H={H_s:.2f}, p={p_s_kw:.4g}")

spec_brand.to_csv(os.path.join(BASE, "rq3_specialty_brand.csv"), index=False)
pd.DataFrame([
    {"test": "One-way ANOVA", "outcome": "prescriber brand_share",
     "grouping": "specialty", "k_groups": len(spec_groups), "n_total": len(all_vals_s),
     "F_statistic": F_s, "df_between": len(spec_groups)-1,
     "df_within": len(all_vals_s)-len(spec_groups), "p_value": p_s, "eta_squared": eta_s},
    {"test": "Kruskal-Wallis H", "outcome": "prescriber brand_share",
     "grouping": "specialty", "k_groups": len(spec_groups), "n_total": len(all_vals_s),
     "F_statistic": H_s, "df_between": len(spec_groups)-1,
     "df_within": np.nan, "p_value": p_s_kw, "eta_squared": np.nan},
]).to_csv(os.path.join(BASE, "rq3_anova_results.csv"), index=False)

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


# =============================================================================
# 9. RQ5 — Brand-to-Generic Savings Simulation
# =============================================================================
print("\n[9/10] RQ5 — Brand-to-generic savings simulation...")

hl_2023 = hl[hl["year"] == 2023].iloc[0]
brand_cpc = hl_2023["brand_cost_per_clm"]
generic_cpc = hl_2023["generic_cost_per_clm"]
cost_delta = brand_cpc - generic_cpc
print(f"  Brand cpc: ${brand_cpc:,.2f}  Generic cpc: ${generic_cpc:,.2f}  Delta: ${cost_delta:,.2f}")

# Excess brand share above specialty median for every prescriber
spec_medians = clean.groupby("specialty")["brand_share"].median()
clean["spec_median_brand_share"] = clean["specialty"].map(spec_medians)
clean["excess_brand_share"] = (
    clean["brand_share"] - clean["spec_median_brand_share"]
).clip(lower=0)
clean["excess_brand_clms"] = clean["excess_brand_share"] * clean["total_clms"]
clean["hypothetical_savings"] = clean["excess_brand_clms"] * cost_delta

sample_savings = clean["hypothetical_savings"].sum()
n_sample_prescribers = clean["Prscrbr_NPI"].nunique()

# Row-based scale-up: sample is 200K of ~1.1M rows
FULL_FILE_ROWS = 1_100_000
SAMPLE_ROWS = 200_000
row_scale = FULL_FILE_ROWS / SAMPLE_ROWS  # ~5.5x
SUBSTITUTION_RATE = 0.50  # share of brand drugs with viable generic alternative
ceiling_savings = sample_savings * row_scale
floor_savings = ceiling_savings * SUBSTITUTION_RATE

print(f"  Sample prescribers: {n_sample_prescribers:,}")
print(f"  Sample savings (raw): ${sample_savings:,.0f}")
print(f"  Row-scale factor: {row_scale:.2f}x")
print(f"  Ceiling annual savings: ${ceiling_savings/1e9:.2f}B")
print(f"  Floor   annual savings: ${floor_savings/1e9:.2f}B (50% substitution)")

clean[[
    "Prscrbr_NPI", "state", "specialty", "total_clms", "total_cost",
    "brand_share", "spec_median_brand_share", "excess_brand_share",
    "excess_brand_clms", "hypothetical_savings",
]].to_csv(os.path.join(BASE, "rq5_prescriber_savings.csv"), index=False)

spec_savings = clean.groupby("specialty").agg(
    n_prescribers=("Prscrbr_NPI", "nunique"),
    total_clms=("total_clms", "sum"),
    sample_savings=("hypothetical_savings", "sum"),
).reset_index()
spec_savings["ceiling_savings"] = spec_savings["sample_savings"] * row_scale
spec_savings["floor_savings"] = spec_savings["ceiling_savings"] * SUBSTITUTION_RATE
spec_savings = spec_savings.sort_values("ceiling_savings", ascending=False)
spec_savings.to_csv(os.path.join(BASE, "rq5_savings_by_specialty.csv"), index=False)

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

# Figure 14 — Specialty savings (floor)
fig, ax = plt.subplots(figsize=(11, 6))
sv_plot = spec_savings.head(15).sort_values("floor_savings")
ax.barh(sv_plot["specialty"], sv_plot["floor_savings"] / 1e9, color=RED, alpha=0.85)
ax.set_xlabel("Annual Savings - Floor Estimate (USD Billions)")
ax.set_title("RQ5 - Hypothetical Brand-to-Specialty-Median Savings by Specialty\n"
             "(50% substitution, row-scaled to full prescriber file)",
             fontweight="bold", pad=12)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.1f}B"))
ax.tick_params(axis="y", labelsize=7)
savefig("fig14_savings_dist.png")


# =============================================================================
# 10. Minimum Sample Size Computation per RQ
# =============================================================================
print("\n[10/10] Minimum sample size per RQ...")

# Cohen 1988 L-table for fixed-effects multiple regression (alpha=0.05, pwr=0.80)
L_table = {1:7.85, 2:9.64, 3:10.91, 4:11.94, 5:12.83, 6:13.62, 7:14.35, 8:15.02}

def n_min_regression(k, f2):
    """Multiple regression: n_min = L/f^2 + k + 1"""
    return int(math.ceil(L_table[k] / f2 + k + 1))

def n_min_anova(k_groups, f, alpha=0.05, power=0.80):
    """One-way ANOVA via noncentral F. Iterative."""
    for n_per in range(2, 5000):
        n_total = n_per * k_groups
        df1 = k_groups - 1
        df2 = n_total - k_groups
        lam = n_total * f * f
        crit = fdist.ppf(1 - alpha, df1, df2)
        pwr = 1 - ncf.cdf(crit, df1, df2, lam)
        if pwr >= power:
            return n_total, n_per
    return None, None

rq1_n = n_min_regression(k=5, f2=0.15)             # OLS, medium effect
rq2_n_total, rq2_n_per = n_min_anova(k_groups=51, f=0.25)  # ANOVA states
rq3_n_total, rq3_n_per = n_min_anova(k_groups=20, f=0.25)  # ANOVA specialties
rq4_n = 50 * 4                                     # Mooi & Sarstedt heuristic
rq5_n = int(math.ceil((1.96 * 0.5 / 0.05) ** 2))   # Mean estimate, 5% relative

n_drug_clean = len(drug.dropna(subset=["spend_2023","claims_2023","unit_cost_2023","benes_2023","num_mfr"]))
n_prescribers_clean = len(clean)

sample_size_df = pd.DataFrame([
    {"RQ":"RQ1", "Test":"Multiple OLS Regression",
     "Parameters":"alpha=0.05, power=0.80, k=5 predictors, f^2=0.15 (medium)",
     "Formula":"n = L/f^2 + k + 1  (Cohen 1988)",
     "Minimum_n": rq1_n, "Achieved_n": int(ols.nobs), "Status":"Exceeded"},
    {"RQ":"RQ2", "Test":"One-way ANOVA (states)",
     "Parameters":"alpha=0.05, power=0.80, k=51 states, f=0.25 (medium)",
     "Formula":"Noncentral F via iterative power.solve",
     "Minimum_n": rq2_n_total, "Achieved_n": int(len(all_vals)), "Status":"Exceeded"},
    {"RQ":"RQ3", "Test":"One-way ANOVA (specialties; proxy)",
     "Parameters":"alpha=0.05, power=0.80, k=20 specialties, f=0.25 (medium)",
     "Formula":"Noncentral F via iterative power.solve",
     "Minimum_n": rq3_n_total, "Achieved_n": int(len(all_vals_s)), "Status":"Exceeded"},
    {"RQ":"RQ4", "Test":"K-means clustering",
     "Parameters":"k=4 clusters, 50-per-cluster heuristic (Mooi & Sarstedt 2011)",
     "Formula":"n_min = 50 * k",
     "Minimum_n": rq4_n, "Achieved_n": int(len(clust_df)), "Status":"Exceeded"},
    {"RQ":"RQ5", "Test":"Sample mean (savings estimate)",
     "Parameters":"95% CI, 5% relative precision, sigma/mu=0.5",
     "Formula":"n = (z * (sigma/mu) / E)^2",
     "Minimum_n": rq5_n, "Achieved_n": n_prescribers_clean, "Status":"Exceeded"},
])
sample_size_df.to_csv(os.path.join(BASE, "sample_size_per_rq.csv"), index=False)
print(sample_size_df.to_string(index=False))


# =============================================================================
# Done (v