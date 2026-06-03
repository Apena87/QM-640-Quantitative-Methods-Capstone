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
from matplotlib.gridspec import GridSpec
from matplotlib.colors import LinearSegmentedColormap

FS = os.path.join(DL, "Final Submission", "data")

NAVY, RED, STEEL, GOLD, GRAY = "#17375E", "#C00000", "#2E75B6", "#F0B429", "#5A6478"

# ──────────────────────────────────────────────────────────────────────────
# Fig 15 — Choropleth
# ──────────────────────────────────────────────────────────────────────────
print("Loading state-level brand share...")
sb = pd.read_csv(os.path.join(FS, "rq2_state_brand_share.csv"))
sb = sb[sb["n_prescribers"] >= 100].copy()
# Restrict to 50 states + DC for clean mapping
real_states = set(["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"])
sb = sb[sb["state"].isin(real_states)].copy()

try:
    import plotly.express as px
    import plotly.io as pio
    sb["weighted_brand_pct"] = sb["weighted_brand_share"] * 100
    fig = px.choropleth(
        sb, locations="state", locationmode="USA-states",
        color="weighted_brand_pct",
        scope="usa",
        color_continuous_scale=[[0, STEEL], [0.5, "#FFF6BF"], [1, RED]],
        labels={"weighted_brand_pct": "Brand share (%)"},
        title="Claim-weighted prescriber brand share by state (full prescriber file)",
        range_color=[sb["weighted_brand_pct"].min(), sb["weighted_brand_pct"].max()],
    )
    fig.update_layout(geo=dict(bgcolor="white"), font=dict(family="DejaVu Sans"),
                      title_font=dict(size=16), height=600, width=1100)
    # Annotate top/bottom states
    for state, pct in zip(sb.nlargest(3,"weighted_brand_pct")["state"],
                          sb.nlargest(3,"weighted_brand_pct")["weighted_brand_pct"]):
        pass
    out = os.path.join(FIG, "fig15_choropleth.png")
    pio.write_image(fig, out, scale=2)
    print(f"Saved {out} via plotly")
except (ImportError, Exception) as e:
    print(f"Plotly choropleth failed ({type(e).__name__}: {e}); building matplotlib bar fallback")
    # Fallback: horizontal bar sorted by brand share, color-graded
    sb = sb.sort_values("weighted_brand_share", ascending=True)
    cmap = LinearSegmentedColormap.from_list("brand", [STEEL, "#FFF6BF", RED])
    vmin, vmax = sb["weighted_brand_share"].min(), sb["weighted_brand_share"].max()
    norm = (sb["weighted_brand_share"] - vmin) / (vmax - vmin)
    colors = [cmap(v) for v in norm]
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.barh(sb["state"], sb["weighted_brand_share"]*100, color=colors)
    ax.set_xlabel("Claim-weighted brand share (%)", fontsize=12)
    ax.set_title("Claim-weighted prescriber brand share by state (full prescriber file)",
                 fontweight="bold", fontsize=14)
    for i, v in enumerate(sb["weighted_brand_share"]*100):
        ax.text(v + 0.1, i, f"{v:.1f}%", va="center", fontsize=8, color=NAVY)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "fig15_choropleth.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved fig15_choropleth.png via matplotlib fallback")


# ──────────────────────────────────────────────────────────────────────────
# Fig 16 — Joint scatter with marginal histograms for outlier prescribers
# ──────────────────────────────────────────────────────────────────────────
print("\nLoading full NPI file for outlier scatter...")
df = pd.read_csv(os.path.join(FS, "prescribers_full_npi.csv"))
p = df.groupby("Prscrbr_NPI", as_index=False).agg(
    total_clms=("total_clms","sum"),
    brand_clms=("brand_clms","sum"),
    specialty=("Prscrbr_Type","first"),
)
p["brand_share"] = p["brand_clms"] / p["total_clms"]
p = p.dropna(subset=["brand_share"])
p = p[p["total_clms"] >= 20]
p["log_total_clms"] = np.log10(p["total_clms"])
print(f"Plotting {len(p):,} prescribers")

# Outlier definition: top decile on BOTH dimensions
clm_90 = p["log_total_clms"].quantile(0.90)
brn_90 = p["brand_share"].quantile(0.90)
p["is_outlier"] = (p["log_total_clms"] >= clm_90) & (p["brand_share"] >= brn_90)
n_out = int(p["is_outlier"].sum())
print(f"Top-decile-on-both outliers: {n_out:,} ({n_out/len(p)*100:.1f}%)")

# Subsample non-outliers for plotting (1M points crashes matplotlib)
sample_n = 50_000
rng = np.random.default_rng(42)
non_out = p[~p["is_outlier"]]
sample = non_out.sample(min(sample_n, len(non_out)), random_state=42)
plot_df = pd.concat([sample, p[p["is_outlier"]]], ignore_index=True)

# Build the layout: scatter center, hist top, hist right
fig = plt.figure(figsize=(11, 8.5))
gs = GridSpec(4, 4, hspace=0.05, wspace=0.05)
ax_main = fig.add_subplot(gs[1:, :3])
ax_top  = fig.add_subplot(gs[0, :3], sharex=ax_main)
ax_right= fig.add_subplot(gs[1:, 3], sharey=ax_main)

# Main scatter
non_o = plot_df[~plot_df["is_outlier"]]
out_o = plot_df[plot_df["is_outlier"]]
ax_main.scatter(non_o["log_total_clms"], non_o["brand_share"]*100,
                s=4, color=STEEL, alpha=0.25, label="Typical prescribers")
ax_main.scatter(out_o["log_total_clms"], out_o["brand_share"]*100,
                s=14, color=RED, alpha=0.65,
                label=f"High-volume + high-brand outliers (n = {n_out:,})")
ax_main.axvline(clm_90, color=GOLD, lw=1.5, ls="--", alpha=0.7)
ax_main.axhline(brn_90*100, color=GOLD, lw=1.5, ls="--", alpha=0.7)
ax_main.set_xlabel("log₁₀(Total annual claims)", fontsize=12)
ax_main.set_ylabel("Brand share of claims (%)", fontsize=12)
ax_main.legend(fontsize=10, loc="upper right")
ax_main.grid(alpha=0.2)

# Top histogram
ax_top.hist(non_o["log_total_clms"], bins=60, color=STEEL, alpha=0.7, density=True)
ax_top.hist(out_o["log_total_clms"], bins=20, color=RED,   alpha=0.7, density=True)
ax_top.axvline(clm_90, color=GOLD, lw=1.5, ls="--", alpha=0.7)
ax_top.set_ylabel("Density", fontsize=9)
ax_top.tick_params(axis="x", labelbottom=False)
ax_top.set_title("Outlier prescribers: high volume AND high brand share (top decile on both axes)",
                 fontweight="bold", fontsize=12, pad=10)

# Right histogram
ax_right.hist(non_o["brand_share"]*100, bins=60, color=STEEL, alpha=0.7,
              density=True, orientation="horizontal")
ax_right.hist(out_o["brand_share"]*100, bins=20, color=RED, alpha=0.7,
              density=True, orientation="horizontal")
ax_right.axhline(brn_90*100, color=GOLD, lw=1.5, ls="--", alpha=0.7)
ax_right.set_xlabel("Density", fontsize=9)
ax_right.tick_params(axis="y", labelleft=False)

plt.tight_layout()
out = os.path.join(FIG, "fig16_outlier_scatter.png")
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved {out}")
