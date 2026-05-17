
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import logit

DL = "C:\Users\kraam\Downloads"
FS = os.path.join(DL, "Final Submission", "data")

print("Loading prescriber NPI summary...")
pres = pd.read_csv(os.path.join(FS, "prescribers_full_npi.csv"))
# Aggregate to one row per NPI in case the file has duplicates
prescriber = pres.groupby("Prscrbr_NPI", as_index=False).agg(
    state=("Prscrbr_State_Abrvtn","first"),
    specialty=("Prscrbr_Type","first"),
    total_clms=("total_clms","sum"),
    total_cost=("total_cost","sum"),
    brand_clms=("brand_clms","sum"),
    brand_cost=("brand_cost","sum"),
)
prescriber["brand_share"] = np.where(prescriber["total_clms"]>0,
                                      prescriber["brand_clms"]/prescriber["total_clms"], np.nan)
prescriber = prescriber.dropna(subset=["brand_share","specialty"])
prescriber = prescriber[prescriber["total_clms"]>=20]
print(f"  Analyzable prescribers: {len(prescriber):,}")

print("Loading Open Payments NPI summary...")
op = pd.read_csv(os.path.join(FS, "open_payments_npi_summary.csv"))
print(f"  Open Payments NPIs: {len(op):,}")

# Coerce NPI to int for join
prescriber["Prscrbr_NPI"] = prescriber["Prscrbr_NPI"].astype("int64")
op["Prscrbr_NPI"] = pd.to_numeric(op["Prscrbr_NPI"], errors="coerce").astype("Int64")
op = op.dropna(subset=["Prscrbr_NPI"]).astype({"Prscrbr_NPI":"int64"})

# Outer join with indicator for "had any payments"
linked = prescriber.merge(op, on="Prscrbr_NPI", how="left", indicator=True)
linked["has_payments"] = (linked["_merge"] == "both").astype(int)
linked = linked.drop(columns=["_merge"])
# Fill NA payment metrics with 0
for c in ["n_payments","total_payment","meal_payment","speaker_payment",
          "max_single_payment","n_payments_over_1k"]:
    linked[c] = linked[c].fillna(0)

print(f"Linked rows: {len(linked):,}")
print(f"  With any Open Payments record: {linked['has_payments'].sum():,} "
      f"({linked['has_payments'].mean()*100:.1f}%)")
print(f"  Total payment value: ${linked['total_payment'].sum()/1e9:.2f}B")
print(f"  Mean payment among those with payments: "
      f"${linked.loc[linked['has_payments']==1,'total_payment'].mean():.2f}")
linked.to_csv(os.path.join(FS, "rq3_open_payments_join.csv"), index=False)

# ── Outcome variable: above-specialty-median brand share ──
spec_med = linked.groupby("specialty")["brand_share"].median()
linked["spec_median"] = linked["specialty"].map(spec_med)
linked["above_median_brand"] = (linked["brand_share"] > linked["spec_median"]).astype(int)
print(f"Above-specialty-median prescribers: "
      f"{linked['above_median_brand'].sum():,} ({linked['above_median_brand'].mean()*100:.1f}%)")

# Restrict to top 20 specialties to keep the design matrix tractable
spec_volume = linked.groupby("specialty")["total_cost"].sum().sort_values(ascending=False)
top_specs = spec_volume.head(20).index.tolist()
subset = linked[linked["specialty"].isin(top_specs)].copy()
print(f"After restricting to top 20 specialties: {len(subset):,} prescribers")

# Log-transform payment metrics (log1p to handle zeros)
subset["log_total_payment"]   = np.log1p(subset["total_payment"])
subset["log_meal"]            = np.log1p(subset["meal_payment"])
subset["log_speaker"]         = np.log1p(subset["speaker_payment"])
subset["log_n_over_1k"]       = np.log1p(subset["n_payments_over_1k"])
subset["log_n_payments"]      = np.log1p(subset["n_payments"])
subset["log_total_clms"]      = np.log1p(subset["total_clms"])

# Build design matrix with specialty fixed effects (drop one as reference)
X = subset[["log_total_payment","log_meal","log_speaker","log_n_over_1k",
            "log_n_payments","log_total_clms"]].copy()
spec_dum = pd.get_dummies(subset["specialty"], prefix="spec", drop_first=True)
X = pd.concat([X, spec_dum], axis=1).astype(float)
X = sm.add_constant(X)
y = subset["above_median_brand"].astype(float)

print(f"Design matrix: {X.shape}")
print("Fitting logistic regression...")
model = sm.Logit(y, X).fit(disp=False, maxiter=200)
print(f"  Converged: {model.mle_retvals.get('converged', True)}")
print(f"  Pseudo R²: {model.prsquared:.4f}")
print(f"  LL = {model.llf:.1f}, LL_null = {model.llnull:.1f}, "
      f"LR p = {model.llr_pvalue:.4g}")

# Headline coefficients (non-specialty)
focal = ["const","log_total_payment","log_meal","log_speaker","log_n_over_1k",
         "log_n_payments","log_total_clms"]
res = pd.DataFrame({
    "predictor": model.params.index,
    "coefficient": model.params.values,
    "std_err": model.bse.values,
    "z_statistic": model.tvalues.values,
    "p_value": model.pvalues.values,
    "odds_ratio": np.exp(model.params.values),
})
res_focal = res[res["predictor"].isin(focal)].copy()
print("\nFocal coefficients (excluding specialty fixed effects):")
print(res_focal.to_string(index=False))

res.to_csv(os.path.join(FS, "rq3_logistic_results.csv"), index=False)
res_focal.to_csv(os.path.join(FS, "rq3_logistic_focal.csv"), index=False)

pd.DataFrame([{
    "n_total": len(linked),
    "n_with_payments": int(linked["has_payments"].sum()),
    "pct_with_payments": float(linked["has_payments"].mean()*100),
    "n_used_in_logistic": int(len(subset)),
    "n_specialties_modeled": len(top_specs),
    "above_median_outcome_share": float(subset["above_median_brand"].mean()),
    "pseudo_r_squared": float(model.prsquared),
    "log_likelihood": float(model.llf),
    "ll_null": float(model.llnull),
    "lr_p_value": float(model.llr_pvalue),
    "or_log_total_payment": float(np.exp(model.params["log_total_payment"])),
    "or_log_meal": float(np.exp(model.params["log_meal"])),
    "or_log_speaker": float(np.exp(model.params["log_speaker"])),
    "or_log_n_over_1k": float(np.exp(model.params["log_n_over_1k"])),
}]).to_csv(os.path.join(FS, "rq3_logistic_summary.csv"), index=False)

print(f"\nSaved RQ3 logistic outputs to {FS}/")
