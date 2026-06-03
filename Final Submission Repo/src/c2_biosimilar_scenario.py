import os, re
import pandas as pd
import numpy as np


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

drug = pd.read_csv(os.path.join(FS, "drug_spending.csv"))

# Manual labeling: each row gets a reference class and a is_biosimilar flag
# Biosimilars have FDA suffix "-xxxx" appended to the generic name (Inflectra = infliximab-dyyb)
BIOSIMILAR_CLASSES = {
    "Humira (adalimumab)": {
        "reference_substrings": ["humira"],
        "biosimilar_generic_substrings": ["adalimumab-"],
    },
    "Remicade (infliximab)": {
        "reference_substrings": ["remicade"],
        "biosimilar_generic_substrings": ["infliximab-"],
    },
    "Lantus (insulin glargine)": {
        "reference_substrings": ["lantus", "toujeo"],
        "biosimilar_generic_substrings": ["insulin glargine-"],  # FDA suffix only on biosimilars
    },
    "Neulasta (pegfilgrastim)": {
        "reference_substrings": ["neulasta"],
        "biosimilar_generic_substrings": ["pegfilgrastim-"],
    },
    "Procrit/Epogen (epoetin alfa)": {
        "reference_substrings": ["procrit", "epogen"],
        "biosimilar_generic_substrings": ["epoetin alfa-"],
    },
    "Avastin (bevacizumab)": {
        "reference_substrings": ["avastin"],
        "biosimilar_generic_substrings": ["bevacizumab-"],
    },
    "Herceptin (trastuzumab)": {
        "reference_substrings": ["herceptin"],
        "biosimilar_generic_substrings": ["trastuzumab-"],
    },
    "Rituxan (rituximab)": {
        "reference_substrings": ["rituxan"],
        "biosimilar_generic_substrings": ["rituximab-"],
    },
}

def classify(brand, generic):
    bl = (brand or "").lower()
    gl = (generic or "").lower()
    for class_name, spec in BIOSIMILAR_CLASSES.items():
        for ref in spec["reference_substrings"]:
            if ref in bl:
                return class_name, "reference_brand"
        for bio in spec["biosimilar_generic_substrings"]:
            if bio in gl:
                return class_name, "biosimilar"
    return None, None

drug[["bio_class","bio_role"]] = drug.apply(
    lambda r: pd.Series(classify(r["brand_name"], r["generic_name"])), axis=1)
drug["spend_2023"]  = pd.to_numeric(drug["spend_2023"],  errors="coerce")
drug["claims_2023"] = pd.to_numeric(drug["claims_2023"], errors="coerce")

bio = drug[drug["bio_class"].notna() & drug["spend_2023"].notna() & drug["claims_2023"].notna()].copy()
bio.to_csv(os.path.join(FS, "rq5_biosimilar_pairs.csv"), index=False)
print(f"Biosimilar-eligible rows: {len(bio)}")

# Per-class summary
agg = bio.groupby(["bio_class","bio_role"]).agg(
    spend=("spend_2023","sum"),
    claims=("claims_2023","sum"),
    n_drugs=("brand_name","nunique"),
).reset_index()
print("\nPer-class roll-up:")
print(agg.to_string(index=False))

# Pivot for class-level cost-per-claim
piv = agg.pivot_table(index="bio_class", columns="bio_role", values=["spend","claims"]).fillna(0)
piv.columns = ["_".join(c) for c in piv.columns]
piv["ref_cpc"] = piv["spend_reference_brand"] / piv["claims_reference_brand"].replace(0, np.nan)
piv["bio_cpc"] = piv["spend_biosimilar"]      / piv["claims_biosimilar"].replace(0, np.nan)
piv["per_claim_delta"] = piv["ref_cpc"] - piv["bio_cpc"]
piv = piv.reset_index()
print("\nClass-level cost-per-claim:")
print(piv[["bio_class","ref_cpc","bio_cpc","per_claim_delta","spend_reference_brand"]].to_string(index=False))

# Savings scenarios: shift X% of REFERENCE brand claims to biosimilar at the
# biosimilar cost-per-claim. Some classes won't have biosimilar data yet so
# we skip those (per_claim_delta = NaN).
scenarios = [0.30, 0.50, 0.70]
rows = []
for _, r in piv.iterrows():
    if pd.isna(r["per_claim_delta"]) or r["claims_reference_brand"] == 0:
        continue
    for s in scenarios:
        switching_claims = r["claims_reference_brand"] * s
        savings = switching_claims * r["per_claim_delta"]
        rows.append({
            "bio_class": r["bio_class"],
            "substitution_rate": s,
            "switching_claims": switching_claims,
            "per_claim_savings": r["per_claim_delta"],
            "class_total_savings": savings,
            "reference_brand_spend_2023": r["spend_reference_brand"],
            "ref_cpc": r["ref_cpc"],
            "bio_cpc": r["bio_cpc"],
        })
class_savings = pd.DataFrame(rows)
class_savings.to_csv(os.path.join(FS, "rq5_biosimilar_class_savings.csv"), index=False)

# Total biosimilar opportunity
totals = []
for s in scenarios:
    sub = class_savings[class_savings["substitution_rate"] == s]
    totals.append({
        "substitution_rate": s,
        "total_savings_$": sub["class_total_savings"].sum(),
        "n_classes_with_data": len(sub),
    })
total_df = pd.DataFrame(totals)
print("\n=== Biosimilar substitution opportunity (total Part D 2023) ===")
print(total_df.to_string(index=False))

# Save total
v5 = pd.read_csv(os.path.join(FS, "rq5_savings_summary.csv")).iloc[0]
combo_rows = []
for s in scenarios:
    bio_only = class_savings[class_savings["substitution_rate"]==s]["class_total_savings"].sum()
    generic_only = float(v5["ceiling_annual_savings"]) * s  # apply same rate
    combo_rows.append({
        "substitution_rate": s,
        "generic_conversion_savings_$B": generic_only/1e9,
        "biosimilar_conversion_savings_$B": bio_only/1e9,
        "combined_savings_$B": (generic_only + bio_only)/1e9,
    })
combo = pd.DataFrame(combo_rows)
combo.to_csv(os.path.join(FS, "rq5_biosimilar_total.csv"), index=False)
print("\n=== Generic + Biosimilar combined opportunity ===")
print(combo.to_string(index=False))
