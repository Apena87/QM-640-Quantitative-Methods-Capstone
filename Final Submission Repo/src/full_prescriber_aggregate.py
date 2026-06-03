import os
import sys
import time
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


NPI_CSV = os.path.join(
    DL, "Medicare Part D Prescribers - by Provider and Drug",
    "Medicare Part D Prescribers - by Provider and Drug",
    "2023", "MUP_DPR_RY25_P04_V10_DY23_NPIBN.csv",
)
WORK = "/tmp/full_prescriber_work"
OUT = os.path.join(DL, "Final Submission", "data", "prescribers_full_npi.csv")
os.makedirs(WORK, exist_ok=True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

USECOLS = [
    "Prscrbr_NPI", "Prscrbr_State_Abrvtn", "Prscrbr_Type",
    "Brnd_Name", "Gnrc_Name",
    "Tot_Clms", "Tot_Drug_Cst",
]
DTYPES = {
    "Prscrbr_NPI": "int64",
    "Prscrbr_State_Abrvtn": "category",
    "Prscrbr_Type": "category",
    "Brnd_Name": "string",
    "Gnrc_Name": "string",
    "Tot_Clms": "float32",
    "Tot_Drug_Cst": "float64",
}
CHUNKSIZE = 3_000_000        # ~9 chunks total
TIME_BUDGET = 35.0           # seconds; exit after this many seconds

# Resume state
done_marker = os.path.join(WORK, "ALL_DONE")
if os.path.exists(done_marker):
    print("All chunks already complete. Combining...")
else:
    # How many chunks already saved?
    existing = sorted(f for f in os.listdir(WORK) if f.startswith("chunk_"))
    start_chunk = len(existing)
    print(f"Found {start_chunk} chunks already saved. Starting from chunk {start_chunk}.")

    t0 = time.time()
    chunk_iter = pd.read_csv(NPI_CSV, usecols=USECOLS, dtype=DTYPES,
                              chunksize=CHUNKSIZE, low_memory=False,
                              skiprows=range(1, 1 + start_chunk * CHUNKSIZE) if start_chunk else None)

    for ci, chunk in enumerate(chunk_iter, start=start_chunk):
        ts = time.time()
        # Brand flag (case-insensitive)
        b = chunk["Brnd_Name"].fillna("").str.strip().str.lower()
        g = chunk["Gnrc_Name"].fillna("").str.strip().str.lower()
        bf = (b != g).astype("int8")
        chunk["brand_clms_row"] = chunk["Tot_Clms"] * bf
        chunk["brand_cost_row"] = chunk["Tot_Drug_Cst"] * bf

        grouped = chunk.groupby(
            ["Prscrbr_NPI", "Prscrbr_State_Abrvtn", "Prscrbr_Type"],
            observed=True
        ).agg(
            total_clms=("Tot_Clms",       "sum"),
            total_cost=("Tot_Drug_Cst",   "sum"),
            brand_clms=("brand_clms_row", "sum"),
            brand_cost=("brand_cost_row", "sum"),
            n_drugs   =("Tot_Clms",       "count"),
        ).reset_index()

        out_path = os.path.join(WORK, f"chunk_{ci:03d}.pkl")
        grouped.to_pickle(out_path)
        print(f"  chunk {ci:3d}: rows={len(chunk):,} groups={len(grouped):,} "
              f"time={time.time()-ts:.1f}s total={time.time()-t0:.1f}s")

        # If chunk is smaller than CHUNKSIZE, we're done
        if len(chunk) < CHUNKSIZE:
            with open(done_marker, "w") as f:
                f.write("done\n")
            print("Reached end of file.")
            break

        # Respect time budget
        if time.time() - t0 > TIME_BUDGET:
            print(f"Time budget hit ({TIME_BUDGET}s). Saving state and exiting; "
                  "re-run script to continue.")
            sys.exit(0)
    else:
        with open(done_marker, "w") as f:
            f.write("done\n")
        print("Iterator exhausted.")

# Combine all chunks
print("\nCombining all chunks...")
parts = []
for f in sorted(os.listdir(WORK)):
    if f.startswith("chunk_"):
        parts.append(pd.read_pickle(os.path.join(WORK, f)))
combined = pd.concat(parts, ignore_index=True)
del parts
print(f"Combined rows (before final groupby): {len(combined):,}")

final = combined.groupby(
    ["Prscrbr_NPI", "Prscrbr_State_Abrvtn", "Prscrbr_Type"],
    observed=True
).agg(
    total_clms=("total_clms", "sum"),
    total_cost=("total_cost", "sum"),
    brand_clms=("brand_clms", "sum"),
    brand_cost=("brand_cost", "sum"),
    n_drugs   =("n_drugs",    "sum"),
).reset_index()

final["brand_share"] = np.where(
    final["total_clms"] > 0,
    final["brand_clms"] / final["total_clms"],
    np.nan
)

print(f"Final rows: {len(final):,}")
print(f"Unique NPIs: {final['Prscrbr_NPI'].nunique():,}")
print(f"Total claims: {final['total_clms'].sum():,.0f}")
print(f"Total cost: ${final['total_cost'].sum()/1e9:.2f}B")
print(f"Overall brand share: {final['brand_clms'].sum()/final['total_clms'].sum()*100:.2f}%")

final.to_csv(OUT, index=False)
print(f"\nSaved: {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")
