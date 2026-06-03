import os
import numpy as np
import pandas as pd
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


NAVY  = "#17375E"
STEEL = "#2E75B6"
TEAL  = "#00B0F0"
RED   = "#C00000"
GOLD  = "#F0B429"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 160,
})

def savefig(name):
    plt.tight_layout()
    out = os.path.join(FIG, name)
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"  Saved {out}")

# ── Fig 12 slide version: top 10 + bottom 10 states with a gap ─────────────
print("Regenerating fig12 (state brand share, slide version)...")
sb = pd.read_csv(os.path.join(DATA, "rq2_state_brand_share.csv"))
sb = sb[sb["n_prescribers"] >= 100].copy()
sb = sb.sort_values("weighted_brand_share", ascending=False)
top10 = sb.head(10)
bot10 = sb.tail(10).sort_values("weighted_brand_share", ascending=False)

fig, ax = plt.subplots(figsize=(14, 5.0))   # 2.8:1 ratio — fits 12×4 slot nicely
# Combine top and bottom with a labeled gap
spacer = pd.DataFrame({"state": ["..."], "weighted_brand_share": [np.nan]})
combo = pd.concat([top10, spacer, bot10], ignore_index=True)
labels = combo["state"].values
values = combo["weighted_brand_share"].values * 100
colors = []
for i, v in enumerate(values):
    if np.isnan(v):
        colors.append("#FFFFFF")
    elif i < 10:
        colors.append(RED)
    else:
        colors.append(TEAL)

y_pos = np.arange(len(combo))
ax.barh(y_pos, np.nan_to_num(values, nan=0), color=colors, edgecolor="none")
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=11)
ax.invert_yaxis()
ax.set_xlabel("Brand Share of Claims (%)", fontsize=12)
ax.set_title("Claim-Weighted Brand Share by State (Top 10 vs. Bottom 10, Full Prescriber File)",
             fontweight="bold", fontsize=13, pad=10)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
# Annotate values
for i, v in enumerate(values):
    if not np.isnan(v):
        ax.text(v + 0.3, i, f"{v:.1f}%", va="center", fontsize=10, color=NAVY)
# Section labels
ax.text(-2, -0.8, "HIGHEST", fontsize=11, color=RED, fontweight="bold")
ax.text(-2, 10.7, "(states omitted)", fontsize=9, color="#888888", style="italic")
ax.text(-2, 11.2, "LOWEST", fontsize=11, color=TEAL, fontweight="bold")
ax.set_xlim(left=-3)
savefig("fig12_state_brand_slide.png")

# ── Fig 13 slide version: top 20 specialties at slide aspect ratio ─────────
print("Regenerating fig13 (specialty brand share, slide version)...")
sp = pd.read_csv(os.path.join(DATA, "rq3_specialty_brand.csv"))
sp = sp.sort_values("weighted_brand_share", ascending=True)   # ascending for horizontal bar

fig, ax = plt.subplots(figsize=(14, 5.0))
y_pos = np.arange(len(sp))
ax.barh(y_pos, sp["weighted_brand_share"]*100, color=NAVY, alpha=0.85)
ax.set_yticks(y_pos)
ax.set_yticklabels(sp["specialty"].values, fontsize=11)
ax.set_xlabel("Brand Share of Claims (%)", fontsize=12)
ax.set_title("Claim-Weighted Brand Share by Specialty (Top 20 by Spend, Full File)",
             fontweight="bold", fontsize=13, pad=10)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
for i, v in enumerate(sp["weighted_brand_share"]*100):
    ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=10, color=NAVY)
savefig("fig13_specialty_brand_slide.png")

# ── Fig 14 slide version: top 15 specialty savings at slide aspect ratio ───
print("Regenerating fig14 (specialty savings, slide version)...")
sv = pd.read_csv(os.path.join(DATA, "rq5_savings_by_specialty.csv"))
sv = sv.head(15).sort_values("floor_savings", ascending=True)
fig, ax = plt.subplots(figsize=(14, 5.0))
y_pos = np.arange(len(sv))
ax.barh(y_pos, sv["floor_savings"]/1e9, color=RED, alpha=0.85)
ax.set_yticks(y_pos)
ax.set_yticklabels(sv["specialty"].values, fontsize=11)
ax.set_xlabel("Annual Savings, Floor Estimate (USD Billions)", fontsize=12)
ax.set_title("RQ5: Floor Annual Savings by Specialty (50% Substitution Assumption)",
             fontweight="bold", fontsize=13, pad=10)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.1f}B"))
for i, v in enumerate(sv["floor_savings"]/1e9):
    ax.text(v + 0.02, i, f"${v:.2f}B", va="center", fontsize=10, color=NAVY)
savefig("fig14_savings_dist_slide.png")

# ── Fig 1 slide version: wide line chart for The Problem slide ─────────────
print("Regenerating fig1 (total cost trend, slide version)...")
hl = pd.read_csv(os.path.join(DATA, "hl_summary.csv"))
years = hl["year"].values
tot   = hl["tot_cost"].values / 1e9
fig, ax = plt.subplots(figsize=(14, 4.5))
ax.fill_between(years, tot, alpha=0.15, color=NAVY)
ax.plot(years, tot, color=NAVY, lw=3, marker="o", ms=7)
for x, y in zip(years, tot):
    ax.annotate(f"${y:.0f}B", (x, y), textcoords="offset points",
                xytext=(0, 9), ha="center", fontsize=10, color=NAVY, fontweight="bold")
ax.set_title("Medicare Part D Total Drug Cost (2013-2023)", fontweight="bold",
             fontsize=14, pad=12)
ax.set_ylabel("USD Billions", fontsize=12)
ax.set_xticks(years)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
ax.tick_params(axis='both', labelsize=11)
ax.set_ylim(top=tot.max() * 1.15)
savefig("fig1_total_cost_trend_slide.png")

# ── Fig 9 slide version: elbow + scatter at slide aspect ratio ─────────────
# The existing fig9 is already 11×4.5 ratio. The slide just placed it too short.
# Just copy the existing one — the slide JS will be updated to give it more height.
import shutil
shutil.copyfile(os.path.join(FIG, "fig9_clustering.png"),
                 os.path.join(FIG, "fig9_clustering_slide.png"))
print("  fig9 reused (already 11x4.5)")

print("\nAll slide figures regenerated.")
