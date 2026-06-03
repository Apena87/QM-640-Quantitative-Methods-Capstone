import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error


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
for c in ["spend_2019","spend_2020","spend_2021","spend_2022","spend_2023",
          "claims_2023","unit_cost_2023","benes_2023","num_mfr"]:
    drug[c] = pd.to_numeric(drug[c], errors="coerce")

# Compute YoY growth rates 2020→2023 (4 transitions); skip 2019→2020 if 2019 missing
def yoy_series(row):
    yrs = [row.get(f"spend_{y}") for y in (2019, 2020, 2021, 2022, 2023)]
    rates = []
    for prev, curr in zip(yrs[:-1], yrs[1:]):
        if prev is None or curr is None or pd.isna(prev) or pd.isna(curr) or prev <= 0:
            rates.append(np.nan)
        else:
            rates.append((curr - prev) / prev)
    return rates

yoy = drug.apply(yoy_series, axis=1, result_type="expand")
yoy.columns = ["yoy_2020","yoy_2021","yoy_2022","yoy_2023"]
drug = pd.concat([drug, yoy], axis=1)

# Velocity = linear slope across the four YoY rates
def velocity(row):
    rates = np.array([row["yoy_2020"], row["yoy_2021"], row["yoy_2022"], row["yoy_2023"]])
    if np.isnan(rates).any():
        return np.nan
    x = np.arange(4)
    # slope via numpy linalg
    coeffs = np.polyfit(x, rates, 1)
    return coeffs[0]   # slope = acceleration of growth

drug["velocity"] = drug.apply(velocity, axis=1)
drug["dollar_growth"] = drug["spend_2023"] - drug["spend_2019"].fillna(0)

n_with_velocity = drug["velocity"].notna().sum()
print(f"Drugs with computable velocity: {n_with_velocity:,} of {len(drug):,}")
print(f"Velocity stats: mean={drug['velocity'].mean():.4f}, sd={drug['velocity'].std():.4f}")
print(f"  positive (accelerating):     {(drug['velocity']>0).sum():,}")
print(f"  negative (decelerating):     {(drug['velocity']<0).sum():,}")

drug[["brand_name","generic_name","yoy_2020","yoy_2021","yoy_2022","yoy_2023","velocity"]].to_csv(
    os.path.join(FS, "rq1_yoy_velocity_data.csv"), index=False)

# Build the OLS sample with all required predictors
md = drug[["spend_2023","claims_2023","unit_cost_2023","benes_2023","num_mfr",
           "spend_2019","velocity"]].copy()
md = md.dropna()
md["dollar_growth"] = md["spend_2023"] - md["spend_2019"].fillna(0)
md = md[(md["spend_2023"]>0)&(md["claims_2023"]>0)&(md["unit_cost_2023"]>0)&(md["benes_2023"]>0)]
print(f"OLS analytic sample (with velocity): n = {len(md):,}")

y = np.log(md["spend_2023"].values)

# Model A: original 5 predictors
X_a = pd.DataFrame({
    "log_claims": np.log(md["claims_2023"]),
    "log_unit_cost": np.log(md["unit_cost_2023"]),
    "log_bene": np.log(md["benes_2023"]),
    "num_mfr": md["num_mfr"],
    "log_dollar_growth": np.log(md["dollar_growth"].clip(lower=1)),
})
X_a_sm = sm.add_constant(X_a)
model_a = sm.OLS(y, X_a_sm).fit()

# Model B: 5 + velocity
X_b = X_a.copy()
X_b["velocity"] = md["velocity"].values
X_b_sm = sm.add_constant(X_b)
model_b = sm.OLS(y, X_b_sm).fit()

print("\n=== Model A (5 predictors, no velocity) ===")
print(f"R² = {model_a.rsquared:.4f}, adj R² = {model_a.rsquared_adj:.4f}, AIC = {model_a.aic:.1f}")
print("\n=== Model B (6 predictors, with velocity) ===")
print(f"R² = {model_b.rsquared:.4f}, adj R² = {model_b.rsquared_adj:.4f}, AIC = {model_b.aic:.1f}")
print(f"Velocity coef: {model_b.params['velocity']:.4f}, p = {model_b.pvalues['velocity']:.4g}")

# K-fold CV for Model B
kf = KFold(n_splits=5, shuffle=True, random_state=42)
fold_r2, fold_rmse = [], []
X_b_arr = X_b_sm.values
for tr, te in kf.split(X_b_arr):
    coefs, _, _, _ = np.linalg.lstsq(X_b_arr[tr], y[tr], rcond=None)
    y_hat = X_b_arr[te] @ coefs
    fold_r2.append(r2_score(y[te], y_hat))
    fold_rmse.append(np.sqrt(mean_squared_error(y[te], y_hat)))
print(f"5-fold CV (Model B): mean R² = {np.mean(fold_r2):.4f} (sd {np.std(fold_r2):.4f}), "
      f"RMSE = {np.mean(fold_rmse):.4f}")

# Save Model B coefficients
res_b = pd.DataFrame({
    "predictor": model_b.params.index,
    "coefficient": model_b.params.values,
    "std_err": model_b.bse.values,
    "t_statistic": model_b.tvalues.values,
    "p_value": model_b.pvalues.values,
    "ci_lower_95": model_b.conf_int()[0].values,
    "ci_upper_95": model_b.conf_int()[1].values,
})
res_b.to_csv(os.path.join(FS, "rq1_ols_with_velocity.csv"), index=False)

# Save comparison
pd.DataFrame([
    {"model":"Model A (5 predictors)", "n":int(model_a.nobs), "r_squared":model_a.rsquared,
     "adj_r_squared":model_a.rsquared_adj, "aic":model_a.aic, "bic":model_a.bic,
     "f_statistic":model_a.fvalue, "f_p_value":model_a.f_pvalue},
    {"model":"Model B (6 predictors, +velocity)", "n":int(model_b.nobs), "r_squared":model_b.rsquared,
     "adj_r_squared":model_b.rsquared_adj, "aic":model_b.aic, "bic":model_b.bic,
     "f_statistic":model_b.fvalue, "f_p_value":model_b.f_pvalue,
     "cv_mean_r_squared":np.mean(fold_r2), "cv_sd_r_squared":np.std(fold_r2),
     "velocity_coef":model_b.params["velocity"], "velocity_p":model_b.pvalues["velocity"]},
]).to_csv(os.path.join(FS, "rq1_ols_comparison.csv"), index=False)
print("\nSaved comparison and coefficient files.")
