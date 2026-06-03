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
hl   = pd.read_csv(os.path.join(FS, "hl_summary.csv"))
df   = pd.read_csv(os.path.join(FS, "prescribers_full_npi.csv"))

# Reproduce the v5 substitutable-pair cost differential from rq5_savings_summary
r5_v5 = pd.read_csv(os.path.join(FS, "rq5_savings_summary.csv")).iloc[0]
DELTA = float(r5_v5["cost_delta_substitutable"])
SUB_RATE = 0.50

# Aggregate to per-NPI level
p = df.groupby("Prscrbr_NPI", as_index=False).agg(
    state=("Prscrbr_State_Abrvtn","first"),
    specialty=("Prscrbr_Type","first"),
    total_clms=("total_clms","sum"),
    total_cost=("total_cost","sum"),
    brand_clms=("brand_clms","sum"),
    brand_cost=("brand_cost","sum"),
)
p["brand_share"] = np.where(p["total_clms"]>0,
                             p["brand_clms"]/p["total_clms"], np.nan)
clean = p.dropna(subset=["brand_share","state","specialty"]).copy()
clean = clean[clean["total_clms"]>=20]
print(f"Analyzable prescribers: {len(clean):,}")

# Need at least 20 prescribers in a state-specialty cell for the median to be stable
cell_counts = clean.groupby(["state","specialty"]).size().reset_index(name="n_cell")
qualifying  = cell_counts[cell_counts["n_cell"]>=20]
print(f"State-specialty cells: {len(cell_counts):,} total, "
      f"{len(qualifying):,} with n>=20 prescribers")

clean_qual = clean.merge(qualifying[["state","specialty"]], on=["state","specialty"], how="inner")
print(f"Prescribers in qualifying state-specialty cells: {len(clean_qual):,}")

# Per-prescriber benchmark: median brand share within (state, specialty)
benchmarks = clean_qual.groupby(["state","specialty"])["brand_share"].median().reset_index()
benchmarks.columns = ["state","specialty","ss_median_brand_share"]
clean_qual = clean_qual.merge(benchmarks, on=["state","specialty"], how="left")

clean_qual["excess_brand_share"] = (clean_qual["brand_share"] -
                                     clean_qual["ss_median_brand_share"]).clip(lower=0)
clean_qual["excess_brand_clms"]  = clean_qual["excess_brand_share"] * clean_qual["total_clms"]
clean_qual["hypothetical_savings"] = clean_qual["excess_brand_clms"] * DELTA

ceiling_ss = clean_qual["hypothetical_savings"].sum()
print(f"\nState+Specialty ceiling savings: ${ceiling_ss/1e9:.2f}B")

# Bootstrap
print("Running 1,000-iter bootstrap...")
rng = np.random.default_rng(42)
sv = clean_qual["hypothetical_savings"].values
n = len(sv)
boot = np.empty(1000)
for i in range(1000):
    boot[i] = sv[rng.integers(0, n, n)].sum()
ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])
floor_ss = ceiling_ss * SUB_RATE
floor_lo, floor_hi = ci_lo * SUB_RATE, ci_hi * SUB_RATE

print(f"State+Specialty floor (50% sub): ${floor_ss/1e9:.2f}B "
      f"(95% CI ${floor_lo/1e9:.2f}-${floor_hi/1e9:.2f}B)")

# Save per-prescriber
clean_qual[[
    "Prscrbr_NPI","state","specialty","total_clms","total_cost","brand_share",
    "ss_median_brand_share","excess_brand_share","excess_brand_clms","hypothetical_savings"
]].to_csv(os.path.join(FS, "rq5_state_specialty_savings.csv"), index=False)

# Save summary
pd.DataFrame([{
    "benchmark_type": "state_specialty_median",
    "n_prescribers_analyzed": int(len(clean_qual)),
    "n_state_specialty_cells_with_n20_or_more": int(len(qualifying)),
    "cost_delta_per_clm": DELTA,
    "ceiling_annual_savings": ceiling_ss,
    "ceiling_ci_lower_95": ci_lo,
    "ceiling_ci_upper_95": ci_hi,
    "floor_annual_savings_50pct_sub": floor_ss,
    "floor_ci_lower_95": floor_lo,
    "floor_ci_upper_95": floor_hi,
}]).to_csv(os.path.join(FS, "rq5_state_specialty_summary.csv"), index=False)

# Benchmark comparison (specialty-only from v5 vs state+specialty)
ceiling_v5 = float(r5_v5["ceiling_annual_savings"])
floor_v5   = float(r5_v5["floor_annual_savings_50pct_sub"])
pd.DataFrame([
    {"benchmark":"Specialty median (v5 baseline)", "n_prescribers":int(r5_v5["n_prescribers_analyzed"]),
     "ceiling_$B":ceiling_v5/1e9,
     "floor_$B":floor_v5/1e9,
     "ceiling_ci_lo_$B":float(r5_v5["ceiling_ci_lower_95"])/1e9,
     "ceiling_ci_hi_$B":float(r5_v5["ceiling_ci_upper_95"])/1e9},
    {"benchmark":"State + Specialty median (HRR proxy)", "n_prescribers":int(len(clean_qual)),
     "ceiling_$B":ceiling_ss/1e9,
     "floor_$B":floor_ss/1e9,
     "ceiling_ci_lo_$B":ci_lo/1e9,
     "ceiling_ci_hi_$B":ci_hi/1e9},
]).to_csv(os.path.join(FS, "rq5_benchmark_comparison.csv"), index=False)

print("\n=== Comparison ===")
print(f"v5 specialty-only:        floor=${floor_v5/1e9:.2f}B, ceiling=${ceiling_v5/1e9:.2f}B")
print(f"state+specialty (new):    floor=${floor_ss/1e9:.2f}B, ceiling=${ceiling_ss/1e9:.2f}B")
print(f"Difference: {(floor_ss-floor_v5)/floor_v5*100:+.1f}% on floor")
