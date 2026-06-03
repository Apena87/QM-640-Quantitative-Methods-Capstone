import os
import pandas as pd
import numpy as np
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

FS = os.path.join(DL, "Final Submission", "data")

NAVY, RED, GOLD, STEEL = "#17375E", "#C00000", "#F0B429", "#2E75B6"

# BLS published annual averages
# CPI-U All Urban Consumers (CUUR0000SA0), annual average
# Medical Care CPI (CUUR0000SAM), annual average
cpi = pd.DataFrame([
    # year   cpi_u    cpi_med
    (2013,   232.957, 425.134),
    (2014,   236.736, 435.292),
    (2015,   237.017, 446.752),
    (2016,   240.007, 463.701),
    (2017,   245.120, 475.323),
    (2018,   251.107, 484.749),
    (2019,   255.657, 498.418),
    (2020,   258.811, 518.901),
    (2021,   270.970, 528.467),
    (2022,   292.655, 547.219),
    (2023,   304.702, 564.300),
], columns=["year","cpi_u","cpi_med"])
# Normalize so 2023 = 1.00 (i.e. report values in real 2023 dollars)
cpi["deflator_u"]   = cpi.loc[cpi["year"]==2023, "cpi_u"].values[0]   / cpi["cpi_u"]
cpi["deflator_med"] = cpi.loc[cpi["year"]==2023, "cpi_med"].values[0] / cpi["cpi_med"]
cpi.to_csv(os.path.join(FS, "cpi_index.csv"), index=False)
print(cpi.to_string(index=False))

# Apply to hl_summary
hl = pd.read_csv(os.path.join(FS, "hl_summary.csv"))
hl = hl.merge(cpi[["year","deflator_u","deflator_med"]], on="year", how="left")
for col in ["tot_cost","brand_cost","generic_cost","cost_per_bene",
            "brand_cost_per_clm","generic_cost_per_clm"]:
    hl[f"{col}_real_u"]   = hl[col] * hl["deflator_u"]
    hl[f"{col}_real_med"] = hl[col] * hl["deflator_med"]
hl.to_csv(os.path.join(FS, "hl_summary_real.csv"), index=False)

# Compute the headline real-vs-nominal numbers
def grow_pct(s, c):
    a = s[s["year"]==2013][c].iloc[0]
    b = s[s["year"]==2023][c].iloc[0]
    return (b - a) / a * 100

nom_bene = grow_pct(hl, "cost_per_bene")
real_u_bene = grow_pct(hl, "cost_per_bene_real_u")
real_med_bene = grow_pct(hl, "cost_per_bene_real_med")
nom_total = grow_pct(hl, "tot_cost")
real_u_total = grow_pct(hl, "tot_cost_real_u")
real_med_total = grow_pct(hl, "tot_cost_real_med")

print(f"\n--- Per-beneficiary cost growth 2013-2023 ---")
print(f"  Nominal:           {nom_bene:.1f}%")
print(f"  Real (CPI-U):      {real_u_bene:.1f}%")
print(f"  Real (Medical CPI):{real_med_bene:.1f}%")
print(f"\n--- Total Part D cost growth 2013-2023 ---")
print(f"  Nominal:           {nom_total:.1f}%")
print(f"  Real (CPI-U):      {real_u_total:.1f}%")
print(f"  Real (Medical CPI):{real_med_total:.1f}%")

# Save key numbers for the report
pd.DataFrame([{
    "metric": "per_beneficiary_growth_2013_2023_pct",
    "nominal": nom_bene,
    "real_cpi_u": real_u_bene,
    "real_cpi_medical": real_med_bene,
}, {
    "metric": "total_part_d_growth_2013_2023_pct",
    "nominal": nom_total,
    "real_cpi_u": real_u_total,
    "real_cpi_medical": real_med_total,
}]).to_csv(os.path.join(FS, "cpi_real_growth_summary.csv"), index=False)

# Figure 18 — nominal vs real per-bene cost
years = hl["year"].values
fig, ax = plt.subplots(figsize=(13, 4.5))
ax.plot(years, hl["cost_per_bene"].values, color=NAVY, lw=2.6, marker="o", ms=6,
        label=f"Nominal (+{nom_bene:.0f}%)")
ax.plot(years, hl["cost_per_bene_real_u"].values, color=STEEL, lw=2.6, marker="s", ms=6,
        label=f"Real, CPI-U adjusted (+{real_u_bene:.0f}%)")
ax.plot(years, hl["cost_per_bene_real_med"].values, color=RED, lw=2.6, marker="D", ms=6,
        label=f"Real, Medical CPI adjusted (+{real_med_bene:.0f}%)")
ax.set_title("Medicare Part D per-beneficiary drug cost, 2013-2023 — nominal vs. inflation-adjusted",
             fontweight="bold", fontsize=13, pad=10)
ax.set_ylabel("USD (2023 = base)", fontsize=12)
ax.set_xticks(years)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.legend(fontsize=10, loc="upper left")
ax.grid(alpha=0.25)
plt.tight_layout()
out = os.path.join(FIG, "fig18_real_vs_nominal.png")
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved {out}")
