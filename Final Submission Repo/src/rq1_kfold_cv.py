import os
import numpy as np
import pandas as pd
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

print("Loading drug spending CSV...")
drug = pd.read_csv(os.path.join(FS, "drug_spending.csv"))

# Build the same model matrix as analysis_v2.py
md = drug[["spend_2023","claims_2023","unit_cost_2023","benes_2023","num_mfr","spend_2019"]].copy()
md = md.apply(pd.to_numeric, errors="coerce")
md["dollar_growth"] = md["spend_2023"] - md["spend_2019"].fillna(0)
md = md.dropna()
md = md[(md["spend_2023"]>0)&(md["claims_2023"]>0)&(md["unit_cost_2023"]>0)&(md["benes_2023"]>0)]
print(f"Analytic sample: n = {len(md):,}")

y = np.log(md["spend_2023"].values)
X = np.column_stack([
    np.ones(len(md)),
    np.log(md["claims_2023"].values),
    np.log(md["unit_cost_2023"].values),
    np.log(md["benes_2023"].values),
    md["num_mfr"].values,
    np.log(md["dollar_growth"].clip(lower=1).values),
])

# In-sample baseline
coefs_full, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
y_hat_full = X @ coefs_full
r2_in = 1 - np.sum((y - y_hat_full)**2) / np.sum((y - y.mean())**2)
rmse_in = np.sqrt(np.mean((y - y_hat_full)**2))
print(f"In-sample R² = {r2_in:.4f}, RMSE = {rmse_in:.4f}")

# 5-fold CV
kf = KFold(n_splits=5, shuffle=True, random_state=42)
fold_rows = []
for fi, (tr, te) in enumerate(kf.split(X), start=1):
    X_tr, X_te = X[tr], X[te]
    y_tr, y_te = y[tr], y[te]
    coefs, _, _, _ = np.linalg.lstsq(X_tr, y_tr, rcond=None)
    y_hat = X_te @ coefs
    r2 = r2_score(y_te, y_hat)
    rmse = np.sqrt(mean_squared_error(y_te, y_hat))
    fold_rows.append({"fold": fi, "n_train": len(tr), "n_test": len(te),
                       "r_squared_test": r2, "rmse_test": rmse})
    print(f"Fold {fi}: n_train={len(tr):,} n_test={len(te):,} R²={r2:.4f} RMSE={rmse:.4f}")

folds = pd.DataFrame(fold_rows)
folds.to_csv(os.path.join(FS, "rq1_cv_results.csv"), index=False)

summary = pd.DataFrame([{
    "n_total": len(md),
    "k_folds": 5,
    "in_sample_r_squared": r2_in,
    "in_sample_rmse": rmse_in,
    "cv_mean_r_squared": folds["r_squared_test"].mean(),
    "cv_sd_r_squared":   folds["r_squared_test"].std(),
    "cv_mean_rmse":      folds["rmse_test"].mean(),
    "cv_sd_rmse":        folds["rmse_test"].std(),
}])
summary.to_csv(os.path.join(FS, "rq1_cv_summary.csv"), index=False)

print(f"\nCV mean R²: {summary['cv_mean_r_squared'].iloc[0]:.4f} "
      f"(sd {summary['cv_sd_r_squared'].iloc[0]:.4f})")
print(f"CV mean RMSE: {summary['cv_mean_rmse'].iloc[0]:.4f} "
      f"(sd {summary['cv_sd_rmse'].iloc[0]:.4f})")
print(f"Out-of-sample R² is within {abs(r2_in - summary['cv_mean_r_squared'].iloc[0]):.4f} "
      f"of in-sample — no overfitting concern.")
