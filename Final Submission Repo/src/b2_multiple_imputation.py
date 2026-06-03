import os
import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge
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

print("Loading drug spending file...")
drug = pd.read_csv(os.path.join(FS, "drug_spending.csv"))
for c in ["spend_2023","claims_2023","unit_cost_2023","benes_2023","num_mfr","spend_2019"]:
    drug[c] = pd.to_numeric(drug[c], errors="coerce")
drug["dollar_growth"] = drug["spend_2023"] - drug["spend_2019"].fillna(0)

n_total = len(drug)
n_benes_missing = drug["benes_2023"].isna().sum()
print(f"Total drugs: {n_total:,}")
print(f"Drugs with missing benes_2023: {n_benes_missing:,} ({n_benes_missing/n_total*100:.1f}%)")

# How many drugs are usable in the analysis WITHOUT imputation
md_drop = drug[["spend_2023","claims_2023","unit_cost_2023","benes_2023","num_mfr","dollar_growth"]].dropna()
md_drop = md_drop[(md_drop["spend_2023"]>0)&(md_drop["claims_2023"]>0)
                  &(md_drop["unit_cost_2023"]>0)&(md_drop["benes_2023"]>0)]
print(f"Usable rows after dropping NAs: {len(md_drop):,}")

# Impute missing benes_2023 using IterativeImputer
print("\nFitting IterativeImputer (MICE-style)...")
features_for_imp = drug[["spend_2023","claims_2023","unit_cost_2023","benes_2023",
                          "num_mfr","spend_2019","dollar_growth"]].copy()
features_for_imp["spend_2019"] = features_for_imp["spend_2019"].fillna(0)

# IterativeImputer needs numeric, finite data; replace inf/nan in non-target with reasonable values
# Drop rows where all key fields are missing
features_for_imp = features_for_imp.dropna(subset=["spend_2023","claims_2023","unit_cost_2023"])
features_for_imp = features_for_imp[features_for_imp["spend_2023"]>0]
print(f"Imputable rows (have spend/claims/unit_cost): {len(features_for_imp):,}")

imputer = IterativeImputer(estimator=BayesianRidge(), max_iter=20, random_state=42,
                            initial_strategy="median")
imp_arr = imputer.fit_transform(features_for_imp.values)
features_imp = pd.DataFrame(imp_arr, columns=features_for_imp.columns,
                             index=features_for_imp.index)
# Clamp negative imputed benes to 1 (minimum sensible value)
features_imp["benes_2023"] = features_imp["benes_2023"].clip(lower=1)
n_after_imp = len(features_imp)
n_imp_only  = features_imp["benes_2023"].notna().sum() - features_for_imp["benes_2023"].notna().sum()
print(f"Drugs in imputed dataset: {n_after_imp:,}")
print(f"  of which had benes_2023 imputed: {n_imp_only:,}")

# Run OLS on imputed dataset
md_imp = features_imp[(features_imp["spend_2023"]>0)&(features_imp["claims_2023"]>0)
                       &(features_imp["unit_cost_2023"]>0)&(features_imp["benes_2023"]>0)].copy()
print(f"OLS-eligible after imputation: {len(md_imp):,}")

y_imp = np.log(md_imp["spend_2023"])
X_imp = pd.DataFrame({
    "log_claims":    np.log(md_imp["claims_2023"]),
    "log_unit_cost": np.log(md_imp["unit_cost_2023"]),
    "log_bene":      np.log(md_imp["benes_2023"]),
    "num_mfr":       md_imp["num_mfr"],
    "log_dollar_growth": np.log(md_imp["dollar_growth"].clip(lower=1)),
})
X_imp_sm = sm.add_constant(X_imp)
model_imp = sm.OLS(y_imp, X_imp_sm).fit()

# Original dropped-NA OLS
y_drop = np.log(md_drop["spend_2023"])
X_drop = pd.DataFrame({
    "log_claims":    np.log(md_drop["claims_2023"]),
    "log_unit_cost": np.log(md_drop["unit_cost_2023"]),
    "log_bene":      np.log(md_drop["benes_2023"]),
    "num_mfr":       md_drop["num_mfr"],
    "log_dollar_growth": np.log(md_drop["dollar_growth"].clip(lower=1)),
})
X_drop_sm = sm.add_constant(X_drop)
model_drop = sm.OLS(y_drop, X_drop_sm).fit()

print(f"\n=== Dropped-NA model (current v5 approach) ===")
print(f"R² = {model_drop.rsquared:.4f}, n = {int(model_drop.nobs):,}")
print(f"\n=== Imputed model (MICE-style via IterativeImputer) ===")
print(f"R² = {model_imp.rsquared:.4f}, n = {int(model_imp.nobs):,}")

# Comparison table
comp = pd.DataFrame({
    "predictor": model_drop.params.index,
    "coef_dropped": model_drop.params.values,
    "coef_imputed": model_imp.params.values,
    "p_dropped":    model_drop.pvalues.values,
    "p_imputed":    model_imp.pvalues.values,
    "abs_delta":    np.abs(model_imp.params.values - model_drop.params.values),
})
print("\n=== Coefficient comparison ===")
print(comp.to_string(index=False))

# Save
comp.to_csv(os.path.join(FS, "rq1_imputation_comparison.csv"), index=False)
pd.DataFrame([{
    "metric": "n_total_drugs", "value": n_total
}, {
    "metric": "n_drugs_missing_benes", "value": int(n_benes_missing)
}, {
    "metric": "pct_drugs_missing_benes", "value": float(n_benes_missing/n_total*100)
}, {
    "metric": "n_dropped_NA_approach", "value": int(len(md_drop))
}, {
    "metric": "n_imputed_approach", "value": int(len(md_imp))
}, {
    "metric": "additional_drugs_via_imputation", "value": int(len(md_imp) - len(md_drop))
}, {
    "metric": "r_squared_dropped", "value": float(model_drop.rsquared)
}, {
    "metric": "r_squared_imputed", "value": float(model_imp.rsquared)
}, {
    "metric": "max_coef_abs_change", "value": float(comp["abs_delta"].max())
}]).to_csv(os.path.join(FS, "rq1_imputation_summary.csv"), index=False)

# Save imputed model coefs
pd.DataFrame({
    "predictor": model_imp.params.index,
    "coefficient": model_imp.params.values,
    "std_err": model_imp.bse.values,
    "t_statistic": model_imp.tvalues.values,
    "p_value": model_imp.pvalues.values,
    "ci_lower_95": model_imp.conf_int()[0].values,
    "ci_upper_95": model_imp.conf_int()[1].values,
}).to_csv(os.path.join(FS, "rq1_ols_imputed.csv"), index=False)
print("\nSaved all imputation outputs.")
