import os
import numpy as np
import pandas as pd


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

print("Loading inputs...")
hl     = pd.read_csv(os.path.join(FS, "hl_summary.csv"))
spend  = pd.read_csv(os.path.join(FS, "drug_spending.csv"))
df     = pd.read_csv(os.path.join(FS, "prescribers_full_npi.csv"))

# ── Identify substitutable brand-generic pairs in the drug spending file ──
# A drug row is "generic" if brand_name == generic_name; "brand" otherwise.
spend["is_generic"] = (
    spend["brand_name"].fillna("").str.strip().str.lower()
    == spend["generic_name"].fillna("").str.strip().str.lower()
)
spend["generic_key"] = spend["generic_name"].fillna("").str.strip().str.lower()

# For each generic_key, find brand rows AND a generic row
key_groups = spend.groupby("generic_key")["is_generic"].agg(["sum", "count"])
key_has_generic = key_groups[key_groups["sum"] >= 1].index
key_has_brand   = key_groups[key_groups["count"] - key_groups["sum"] >= 1].index
substitutable_keys = key_has_generic.intersection(key_has_brand)
substitutable_keys = [k for k in substitutable_keys if k]   # drop empty
print(f"Substitutable generic_name groups: {len(substitutable_keys):,}")

# Within these substitutable groups, compute weighted-average brand cost per claim
# and weighted-average generic cost per claim (claim-weighted across years).
# We use 2023 spending and 2023 claims.
sub_spend = spend[spend["generic_key"].isin(substitutable_keys)].copy()
# Brand cpc = sum(brand spend) / sum(brand claims); same for generic
sub_brand   = sub_spend[~sub_spend["is_generic"]]
sub_generic = sub_spend[sub_spend["is_generic"]]
brand_spend_sum   = sub_brand["spend_2023"].sum()
brand_claims_sum  = sub_brand["claims_2023"].sum()
generic_spend_sum = sub_generic["spend_2023"].sum()
generic_claims_sum= sub_generic["claims_2023"].sum()

sub_brand_cpc   = brand_spend_sum   / brand_claims_sum
sub_generic_cpc = generic_spend_sum / generic_claims_sum
sub_delta       = sub_brand_cpc - sub_generic_cpc

print(f"Substitutable brand cpc:   ${sub_brand_cpc:,.2f}")
print(f"Substitutable generic cpc: ${sub_generic_cpc:,.2f}")
print(f"Substitutable cost delta:  ${sub_delta:,.2f}")
print(f"(For comparison: program-wide brand cpc = ${hl[hl['year']==2023].iloc[0]['brand_cost_per_clm']:,.2f}, "
      f"generic cpc = ${hl[hl['year']==2023].iloc[0]['generic_cost_per_clm']:,.2f})")

# Save the substitutable pairs for transparency (top 20 by brand spend)
sub_brand_top = sub_brand.nlargest(20, "spend_2023")[
    ["brand_name", "generic_name", "spend_2023", "claims_2023", "unit_cost_2023"]
]
sub_brand_top.to_csv(os.path.join(FS, "rq5_substitutable_pairs_top20.csv"), index=False)

# Save a fuller pair-level summary
pair_summary = pd.DataFrame({
    "metric": ["substitutable_brand_cpc","substitutable_generic_cpc","substitutable_delta",
               "n_substitutable_generic_groups",
               "n_brand_rows_in_substitutable","n_generic_rows_in_substitutable",
               "program_wide_brand_cpc_2023","program_wide_generic_cpc_2023","program_wide_delta_2023"],
    "value": [sub_brand_cpc, sub_generic_cpc, sub_delta,
              len(substitutable_keys), len(sub_brand), len(sub_generic),
              hl[hl["year"]==2023].iloc[0]["brand_cost_per_clm"],
              hl[hl["year"]==2023].iloc[0]["generic_cost_per_clm"],
              (hl[hl["year"]==2023].iloc[0]["brand_cost_per_clm"]
               - hl[hl["year"]==2023].iloc[0]["generic_cost_per_clm"])],
})
pair_summary.to_csv(os.path.join(FS, "rq5_substitutable_pairs.csv"), index=False)

# ── RQ5 simulation with refined delta ──────────────────────────────────────
print("\nAggregating prescribers...")
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
clean = prescriber.dropna(subset=["brand_share","state","specialty"]).copy()
clean = clean[clean["total_clms"] >= 20]
print(f"Analyzable prescribers: {len(clean):,}")

spec_med = clean.groupby("specialty")["brand_share"].median()
clean["spec_median_brand_share"] = clean["specialty"].map(spec_med)
clean["excess_brand_share"] = (clean["brand_share"] - clean["spec_median_brand_share"]).clip(lower=0)
clean["excess_brand_clms"] = clean["excess_brand_share"] * clean["total_clms"]
clean["hypothetical_savings"] = clean["excess_brand_clms"] * sub_delta

ceiling = clean["hypothetical_savings"].sum()
print(f"Ceiling savings (100% substitutable, refined delta): ${ceiling/1e9:.2f}B")

# Bootstrap
N_BOOT = 1000
rng = np.random.default_rng(42)
sv = clean["hypothetical_savings"].values
n = len(sv)
boot = np.empty(N_BOOT)
for i in range(N_BOOT):
    boot[i] = sv[rng.integers(0, n, n)].sum()
ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])
print(f"Bootstrap 95% CI for ceiling: ${ci_lo/1e9:.2f}B - ${ci_hi/1e9:.2f}B")

# Sensitivity
sub_rates = [0.30, 0.40, 0.50, 0.60, 0.70]
tot_partd_2023 = hl[hl["year"]==2023].iloc[0]["tot_cost"]
sens_rows = []
for r in sub_rates:
    sens_rows.append({
        "substitution_rate": r,
        "point_estimate_annual_savings": ceiling * r,
        "ci_lower_95": ci_lo * r,
        "ci_upper_95": ci_hi * r,
        "pct_of_part_d_2023": (ceiling * r) / tot_partd_2023,
    })
sens = pd.DataFrame(sens_rows)
print("\nSensitivity (refined delta):")
print(sens.to_string(index=False))
sens.to_csv(os.path.join(FS, "rq5_sensitivity.csv"), index=False)

floor_50 = ceiling * 0.5
floor_50_lo, floor_50_hi = ci_lo * 0.5, ci_hi * 0.5

# Save
clean[["Prscrbr_NPI","state","specialty","total_clms","total_cost",
       "brand_share","spec_median_brand_share","excess_brand_share",
       "excess_brand_clms","hypothetical_savings"]].to_csv(
    os.path.join(FS, "rq5_prescriber_savings.csv"), index=False)

ss = clean.groupby("specialty").agg(
    n_prescribers=("Prscrbr_NPI", "nunique"),
    total_clms=("total_clms", "sum"),
    sample_savings=("hypothetical_savings", "sum"),
).reset_index()
ss["ceiling_savings"] = ss["sample_savings"]
ss["floor_savings"]   = ss["ceiling_savings"] * 0.5
ss = ss.sort_values("ceiling_savings", ascending=False)
ss.to_csv(os.path.join(FS, "rq5_savings_by_specialty.csv"), index=False)

pd.DataFrame([{
    "brand_cpc_substitutable": sub_brand_cpc,
    "generic_cpc_substitutable": sub_generic_cpc,
    "cost_delta_substitutable": sub_delta,
    "n_prescribers_analyzed": int(len(clean)),
    "n_substitutable_brand_drugs": int(len(sub_brand)),
    "n_substitutable_generic_groups": int(len(substitutable_keys)),
    "ceiling_annual_savings": ceiling,
    "ceiling_ci_lower_95": ci_lo,
    "ceiling_ci_upper_95": ci_hi,
    "floor_annual_savings_50pct_sub": floor_50,
    "floor_ci_lower_95": floor_50_lo,
    "floor_ci_upper_95": floor_50_hi,
    "n_bootstrap": N_BOOT,
    "substitution_rate_floor": 0.50,
    "pct_of_part_d_2023_floor": floor_50 / tot_partd_2023,
}]).to_csv(os.path.join(FS, "rq5_savings_summary.csv"), index=False)

print(f"\n=== Headline ===")
print(f"Floor (50% substitution): ${floor_50/1e9:.2f}B  "
      f"(95% CI ${floor_50_lo/1e9:.2f}B - ${floor_50_hi/1e9:.2f}B)")
print(f"Ceiling (100%):           ${ceiling/1e9:.2f}B  "
      f"(95% CI ${ci_lo/1e9:.2f}B - ${ci_hi/1e9:.2f}B)")
print(f"Floor as % of Part D 2023: {floor_50/tot_partd_2023*100:.2f}%")
