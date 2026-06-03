import os
import pandas as pd
import numpy as np
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

print("Loading state demographics...")
df = pd.read_csv(os.path.join(FS, "state_demographics.csv"))
print(f"States: {len(df)}")

y = df["weighted_brand_share"].values

# Define predictor blocks
INSURANCE = ["uninsured_pct"]
SDOH      = ["age65_pct","diabetes_pct","htn_pct","obesity_pct","median_hh_inc","college_pct"]
ALL_PRED  = SDOH + INSURANCE

# Rescale income to per $10K for readability
df["median_hh_inc"] = df["median_hh_inc"] / 10000.0

def fit(predictors, name):
    X = sm.add_constant(df[predictors])
    m = sm.OLS(y, X).fit()
    print(f"\n=== {name} ({len(predictors)} predictors) ===")
    print(f"R² = {m.rsquared:.4f}, adj R² = {m.rsquared_adj:.4f}")
    print(f"F({int(m.df_model)}, {int(m.df_resid)}) = {m.fvalue:.2f}, p = {m.f_pvalue:.4g}")
    print(f"AIC = {m.aic:.2f}, BIC = {m.bic:.2f}")
    return m

m1 = fit(INSURANCE, "Model 1: Insurance only")
m2 = fit(SDOH,      "Model 2: SDoH only (6 predictors)")
m3 = fit(ALL_PRED,  "Model 3: Combined SDoH + Insurance (7 predictors)")

# Partial F-tests
# F-change M1 -> M3 = adding SDoH to insurance
ssr_1, df_1 = m1.ssr, m1.df_resid
ssr_3, df_3 = m3.ssr, m3.df_resid
F_add_sdoh = ((ssr_1 - ssr_3) / (df_1 - df_3)) / (ssr_3 / df_3)
from scipy.stats import f as fdist
p_add_sdoh = 1 - fdist.cdf(F_add_sdoh, df_1 - df_3, df_3)
print(f"\nPartial F (adding SDoH block to insurance-only):  F({df_1-df_3},{df_3}) = {F_add_sdoh:.2f}, p = {p_add_sdoh:.4g}")

# F-change M2 -> M3 = adding insurance to SDoH-only
ssr_2, df_2 = m2.ssr, m2.df_resid
F_add_ins = ((ssr_2 - ssr_3) / (df_2 - df_3)) / (ssr_3 / df_3)
p_add_ins = 1 - fdist.cdf(F_add_ins, df_2 - df_3, df_3)
print(f"Partial F (adding insurance to SDoH-only):       F({df_2-df_3},{df_3}) = {F_add_ins:.2f}, p = {p_add_ins:.4g}")

# Summary table
summary = pd.DataFrame([
    {"model":"M1 Insurance only", "n_predictors":len(INSURANCE), "r_squared":m1.rsquared,
     "adj_r_squared":m1.rsquared_adj, "f_stat":m1.fvalue, "f_p":m1.f_pvalue, "aic":m1.aic, "bic":m1.bic},
    {"model":"M2 SDoH only",      "n_predictors":len(SDOH),      "r_squared":m2.rsquared,
     "adj_r_squared":m2.rsquared_adj, "f_stat":m2.fvalue, "f_p":m2.f_pvalue, "aic":m2.aic, "bic":m2.bic},
    {"model":"M3 Combined",       "n_predictors":len(ALL_PRED),  "r_squared":m3.rsquared,
     "adj_r_squared":m3.rsquared_adj, "f_stat":m3.fvalue, "f_p":m3.f_pvalue, "aic":m3.aic, "bic":m3.bic},
])
summary.to_csv(os.path.join(FS, "rq2_hierarchical_summary.csv"), index=False)

partials = pd.DataFrame([
    {"comparison":"M1 -> M3 (add SDoH to insurance-only)",
     "f_change":F_add_sdoh, "p_change":p_add_sdoh,
     "r_squared_gain": m3.rsquared - m1.rsquared},
    {"comparison":"M2 -> M3 (add insurance to SDoH-only)",
     "f_change":F_add_ins, "p_change":p_add_ins,
     "r_squared_gain": m3.rsquared - m2.rsquared},
])
partials.to_csv(os.path.join(FS, "rq2_partial_f_tests.csv"), index=False)

print("\n=== Summary ===")
print(summary.to_string(index=False))
print("\n=== Partial F-tests ===")
print(partials.to_string(index=False))
