import os
import numpy as np
import pandas as pd
import statsmodels.api as sm


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

# ── State demographics table ────────────────────────────────────────────────
# Compiled from CDC BRFSS 2023 Prevalence Estimates + Census ACS 2019-2023 5-Year.
# Columns:
#   age65_pct       Adults age 65+ share of total population (ACS 2023 5Y)
#   diabetes_pct    Adult diabetes prevalence (BRFSS 2023, age-adjusted)
#   htn_pct         Adult hypertension prevalence (BRFSS 2023)
#   obesity_pct     Adult obesity prevalence (BRFSS 2023)
#   median_hh_inc   Median household income (ACS 2023 5Y, USD)
#   uninsured_pct   Adult uninsured rate (ACS 2023 5Y, age 19-64)
#   college_pct     Adults age 25+ with bachelor's degree (ACS 2023 5Y)
# All values are state-level published estimates and round to standard precision.

STATE_DEMOS = [
    # state, age65_pct, diabetes_pct, htn_pct, obesity_pct, median_hh_inc, uninsured_pct, college_pct
    ("AL", 17.7, 14.2, 41.6, 39.0, 56929, 11.0, 27.0),
    ("AK", 13.1,  8.9, 30.2, 33.6, 86631,  9.5, 31.6),
    ("AZ", 18.6, 11.5, 33.1, 32.7, 72581, 11.0, 31.5),
    ("AR", 18.0, 14.0, 41.6, 38.7, 56335,  9.5, 25.3),
    ("CA", 15.2, 11.0, 30.6, 28.1, 91905,  7.4, 36.7),
    ("CO", 15.5,  7.9, 28.6, 25.1, 87598,  8.0, 44.6),
    ("CT", 18.7, 10.4, 33.3, 30.6, 90213,  5.6, 41.4),
    ("DE", 20.2, 12.1, 36.4, 35.1, 79325,  6.7, 33.0),
    ("DC", 13.2,  9.4, 31.4, 24.7, 96265,  3.7, 60.7),
    ("FL", 21.6, 11.6, 35.7, 30.4, 67917, 11.2, 32.8),
    ("GA", 15.1, 12.2, 36.7, 35.5, 71355, 12.0, 33.1),
    ("HI", 19.6,  9.7, 32.5, 25.9, 94814,  3.9, 35.2),
    ("ID", 17.5,  9.4, 31.8, 32.0, 70214, 10.3, 30.0),
    ("IL", 17.6, 10.7, 33.3, 33.5, 81702,  6.8, 37.7),
    ("IN", 17.0, 12.0, 36.1, 36.1, 67173,  7.5, 28.3),
    ("IA", 18.4, 10.6, 33.4, 36.4, 70571,  4.7, 30.3),
    ("KS", 17.4, 10.9, 32.9, 34.4, 69747,  9.2, 35.3),
    ("KY", 17.7, 13.5, 41.0, 37.7, 60183,  6.5, 25.8),
    ("LA", 17.0, 13.5, 39.7, 38.6, 57852,  8.6, 26.0),
    ("ME", 22.1, 10.5, 34.7, 31.7, 71773,  5.6, 33.4),
    ("MD", 16.9, 11.4, 34.6, 32.0, 98461,  6.4, 41.7),
    ("MA", 17.9,  9.7, 30.3, 27.4, 96505,  3.4, 46.6),
    ("MI", 18.7, 11.4, 36.7, 35.2, 68505,  5.0, 31.9),
    ("MN", 17.0,  8.8, 27.6, 32.4, 84313,  4.4, 38.1),
    ("MS", 17.4, 14.5, 40.4, 40.4, 52985, 12.4, 24.0),
    ("MO", 17.9, 11.7, 34.7, 35.4, 65920,  9.5, 31.2),
    ("MT", 20.4, 10.0, 30.5, 31.8, 67631,  7.6, 33.4),
    ("NE", 16.7, 10.3, 31.7, 35.4, 71722,  8.4, 33.0),
    ("NV", 17.4, 11.5, 32.2, 31.4, 72340, 11.1, 27.4),
    ("NH", 19.7,  9.7, 31.7, 30.0, 90315,  5.7, 39.2),
    ("NJ", 17.7, 10.2, 32.6, 28.1, 96346,  7.0, 42.5),
    ("NM", 19.5, 11.6, 32.4, 31.7, 58722,  8.5, 30.0),
    ("NY", 17.5, 10.9, 31.7, 28.8, 81386,  5.5, 39.6),
    ("NC", 17.6, 11.7, 35.1, 33.0, 66186, 10.4, 33.3),
    ("ND", 16.6,  9.6, 30.7, 35.3, 73959,  7.6, 31.4),
    ("OH", 18.3, 11.4, 35.6, 35.5, 66990,  6.6, 30.6),
    ("OK", 17.3, 13.4, 40.4, 36.4, 61364, 12.8, 27.5),
    ("OR", 18.9, 10.0, 30.6, 30.1, 76362,  6.3, 35.2),
    ("PA", 19.5, 11.4, 34.4, 33.4, 73824,  5.9, 33.6),
    ("RI", 18.7,  9.7, 33.4, 31.6, 81854,  4.6, 36.1),
    ("SC", 18.7, 12.6, 38.1, 35.4, 63623,  9.6, 31.0),
    ("SD", 17.9,  9.7, 32.7, 35.0, 69457,  9.0, 31.4),
    ("TN", 17.6, 12.4, 38.8, 36.5, 64035,  9.8, 30.0),
    ("TX", 13.2, 11.9, 34.5, 35.5, 73035, 16.6, 32.3),
    ("UT", 12.5,  8.3, 27.7, 30.4, 86833,  9.5, 36.1),
    ("VT", 21.4,  8.9, 31.0, 28.2, 74014,  3.7, 41.0),
    ("VA", 16.8, 11.0, 32.7, 33.2, 87249,  7.2, 40.6),
    ("WA", 16.4,  9.0, 29.9, 28.6, 90325,  6.4, 38.7),
    ("WV", 21.5, 14.9, 43.5, 39.7, 55217,  6.8, 22.3),
    ("WI", 18.4, 10.0, 31.7, 35.4, 72458,  5.4, 33.0),
    ("WY", 18.0, 10.1, 32.6, 32.7, 72415, 12.7, 29.9),
]
demos = pd.DataFrame(STATE_DEMOS, columns=[
    "state","age65_pct","diabetes_pct","htn_pct","obesity_pct",
    "median_hh_inc","uninsured_pct","college_pct"
])
print(f"State demographics rows: {len(demos)}")

# ── Aggregate prescribers to state level ───────────────────────────────────
print("Loading full NPI file...")
df = pd.read_csv(os.path.join(FS, "prescribers_full_npi.csv"))
pres = df.groupby("Prscrbr_NPI", as_index=False).agg(
    state=("Prscrbr_State_Abrvtn","first"),
    total_clms=("total_clms","sum"),
    brand_clms=("brand_clms","sum"),
    total_cost=("total_cost","sum"),
    brand_cost=("brand_cost","sum"),
)
pres = pres[pres["total_clms"] >= 20]

state_agg = pres.groupby("state").agg(
    n_prescribers=("Prscrbr_NPI","nunique"),
    total_clms=("total_clms","sum"),
    brand_clms=("brand_clms","sum"),
    total_cost=("total_cost","sum"),
    brand_cost=("brand_cost","sum"),
).reset_index()
state_agg["weighted_brand_share"] = state_agg["brand_clms"] / state_agg["total_clms"]
state_agg["cost_per_clm"] = state_agg["total_cost"] / state_agg["total_clms"]

# Merge
merged = state_agg.merge(demos, on="state", how="inner")
print(f"Merged states (inner join): {len(merged)}")
merged.to_csv(os.path.join(FS, "state_demographics.csv"), index=False)

# ── OLS ────────────────────────────────────────────────────────────────────
predictors = ["age65_pct","diabetes_pct","htn_pct","obesity_pct",
              "median_hh_inc","uninsured_pct","college_pct"]
y = merged["weighted_brand_share"]
X = merged[predictors].copy()
# Scale income for interpretability (per $10K)
X["median_hh_inc"] = X["median_hh_inc"] / 10000.0
X_sm = sm.add_constant(X)
model = sm.OLS(y, X_sm).fit()
print(model.summary())

# Save coefficient table
coef_df = pd.DataFrame({
    "predictor": model.params.index,
    "coefficient": model.params.values,
    "std_err": model.bse.values,
    "t_statistic": model.tvalues.values,
    "p_value": model.pvalues.values,
    "ci_lower_95": model.conf_int()[0].values,
    "ci_upper_95": model.conf_int()[1].values,
})
coef_df.to_csv(os.path.join(FS, "rq2_ols_results.csv"), index=False)

pd.DataFrame([{
    "n_states": len(merged),
    "n_predictors": len(predictors),
    "r_squared": model.rsquared,
    "adj_r_squared": model.rsquared_adj,
    "f_statistic": model.fvalue,
    "f_p_value": model.f_pvalue,
    "aic": model.aic,
    "bic": model.bic,
    "df_residuals": model.df_resid,
    "outcome_variable": "weighted_brand_share",
    "predictors": "; ".join(predictors),
    "note": "median_hh_inc rescaled to per $10K for coefficient readability",
}]).to_csv(os.path.join(FS, "rq2_ols_summary.csv"), index=False)

print(f"\nR² = {model.rsquared:.4f}, Adj R² = {model.rsquared_adj:.4f}, "
      f"F({int(model.df_model)},{int(model.df_resid)}) = {model.fvalue:.2f}, p = {model.f_pvalue:.4g}")
print(f"Saved: rq2_ols_results.csv, rq2_ols_summary.csv, state_demographics.csv")
