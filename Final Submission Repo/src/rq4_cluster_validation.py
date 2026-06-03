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
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score

FS = os.path.join(DL, "Final Submission", "data")
os.makedirs(FIG, exist_ok=True)

NAVY, STEEL, RED, GOLD = "#17375E", "#2E75B6", "#C00000", "#F0B429"

print("Loading drug spending file...")
drug = pd.read_csv(os.path.join(FS, "drug_spending.csv"))

# Build feature matrix exactly as in analysis_v2.py RQ4 section
drug["dollar_growth"] = (pd.to_numeric(drug["spend_2023"], errors="coerce")
                         - pd.to_numeric(drug["spend_2019"], errors="coerce").fillna(0))
clust_df = drug[["claims_2023","unit_cost_2023","dollar_growth","spend_2023"]].copy()
clust_df = clust_df.apply(pd.to_numeric, errors="coerce").dropna()
clust_df = clust_df[(clust_df["claims_2023"]>0)&(clust_df["unit_cost_2023"]>0)]

X = np.column_stack([
    np.log(clust_df["claims_2023"].values),
    np.log(clust_df["unit_cost_2023"].values),
    np.log(clust_df["dollar_growth"].clip(lower=1).values),
])
X_scaled = StandardScaler().fit_transform(X)
print(f"n drugs in clustering: {len(X_scaled):,}")

# Silhouette is O(n^2) memory — subsample for that metric only
rng = np.random.default_rng(42)
sub_idx = rng.choice(len(X_scaled), size=min(5000, len(X_scaled)), replace=False)
X_sub = X_scaled[sub_idx]

results = []
for k in range(2, 9):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels_full = km.fit_predict(X_scaled)
    labels_sub  = km.predict(X_sub)
    sil = silhouette_score(X_sub, labels_sub) if k > 1 else np.nan
    dbi = davies_bouldin_score(X_scaled, labels_full)
    wcss = km.inertia_
    results.append({
        "k": k, "wcss": wcss,
        "silhouette_score": sil,
        "davies_bouldin_index": dbi,
        "silhouette_n_subsample": len(sub_idx),
        "n_total": len(X_scaled),
    })
    print(f"  k={k}: WCSS={wcss:.0f}, Silhouette={sil:.4f}, DBI={dbi:.4f}")

df = pd.DataFrame(results)
df.to_csv(os.path.join(FS, "rq4_cluster_validation.csv"), index=False)

# Build validation figure: 3 panels (WCSS, Silhouette, DBI)
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for ax, col, label, color, optimum in [
    (axes[0], "wcss",                 "Within-Cluster SS (lower = tighter)", NAVY,  None),
    (axes[1], "silhouette_score",     "Silhouette Score (higher = better)",   STEEL, "max"),
    (axes[2], "davies_bouldin_index", "Davies-Bouldin Index (lower = better)",RED,   "min"),
]:
    ax.plot(df["k"], df[col], color=color, lw=2.5, marker="o", ms=8)
    ax.set_xlabel("Number of clusters (k)", fontsize=11)
    ax.set_title(label, fontweight="bold", fontsize=11)
    ax.axvline(4, color=GOLD, lw=1.5, ls="--", alpha=0.85, label="Selected k=4")
    ax.legend(fontsize=9, loc="best")
    ax.grid(alpha=0.25)

plt.suptitle("K-means cluster validation: WCSS, Silhouette, and Davies-Bouldin (k = 2 to 8)",
             fontweight="bold", fontsize=13)
plt.tight_layout()
out = os.path.join(FIG, "fig17_cluster_validation.png")
plt.savefig(out, bbox_inches="tight", dpi=150)
plt.close()
print(f"Saved {out}")

# Brief verdict
chosen = df[df["k"]==4].iloc[0]
best_sil = df.loc[df["silhouette_score"].idxmax()]
best_dbi = df.loc[df["davies_bouldin_index"].idxmin()]
print(f"\n=== Verdict ===")
print(f"k=4 chosen by elbow: silhouette={chosen['silhouette_score']:.4f}, DBI={chosen['davies_bouldin_index']:.4f}")
print(f"Best silhouette: k={int(best_sil['k'])} at {best_sil['silhouette_score']:.4f}")
print(f"Best (lowest) DBI: k={int(best_dbi['k'])} at {best_dbi['davies_bouldin_index']:.4f}")
