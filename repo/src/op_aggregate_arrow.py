
import sys, time, os
import pyarrow as pa
import pyarrow.csv as pc
import pyarrow.compute as pcc

OUT = sys.argv[1] if len(sys.argv) > 1 else "C:\Users\kraam\Downloads\tmp\op_npi_summary.csv"

USECOLS = ['Covered_Recipient_Type', 'Covered_Recipient_NPI',
           'Total_Amount_of_Payment_USDollars',
           'Nature_of_Payment_or_Transfer_of_Value']

read_opts = pc.ReadOptions(use_threads=True, block_size=32 << 20)  # 32 MB blocks
parse_opts = pc.ParseOptions(invalid_row_handler=lambda r: 'skip',
                              newlines_in_values=False)
conv_opts = pc.ConvertOptions(
    include_columns=USECOLS,
    column_types={'Covered_Recipient_NPI': pa.string(),
                  'Total_Amount_of_Payment_USDollars': pa.float64()},
)

reader = pc.open_csv(sys.stdin.buffer,
                      read_options=read_opts,
                      parse_options=parse_opts,
                      convert_options=conv_opts)

agg = {}
total_rows = 0
t0 = time.time()
batch_idx = 0
last_log = 0

for batch in reader:
    batch_idx += 1
    n = batch.num_rows
    total_rows += n

    # Filter to physicians with non-null NPI
    mask = pcc.match_substring(batch['Covered_Recipient_Type'], 'Physician')
    mask = pcc.and_(mask, pcc.is_valid(batch['Covered_Recipient_NPI']))
    f = batch.filter(mask)
    if f.num_rows == 0:
        continue

    npis    = f['Covered_Recipient_NPI'].to_pylist()
    amounts = f['Total_Amount_of_Payment_USDollars'].to_pylist()
    natures = f['Nature_of_Payment_or_Transfer_of_Value'].to_pylist()

    for npi, amt, nat in zip(npis, amounts, natures):
        if npi is None: continue
        amt = amt if amt is not None else 0.0
        nat = nat if nat is not None else ''
        rec = agg.get(npi)
        if rec is None:
            rec = [0, 0.0, 0.0, 0.0, 0.0, 0]
            agg[npi] = rec
        rec[0] += 1
        rec[1] += amt
        if 'Food and Beverage' in nat:
            rec[2] += amt
        elif 'Compensation for services' in nat:
            rec[3] += amt
        if amt > rec[4]:
            rec[4] = amt
        if amt > 1000:
            rec[5] += 1

    if total_rows - last_log >= 2_000_000:
        sys.stderr.write(f"batches={batch_idx} rows={total_rows:,} "
                         f"NPIs={len(agg):,} t={time.time()-t0:.1f}s\n")
        sys.stderr.flush()
        last_log = total_rows

# Write output
sys.stderr.write(f"Writing {len(agg):,} NPIs to {OUT}...\n")
import csv as _csv
with open(OUT, "w", newline="") as fout:
    w = _csv.writer(fout)
    w.writerow(["Prscrbr_NPI","n_payments","total_payment","meal_payment",
                "speaker_payment","max_single_payment","n_payments_over_1k"])
    for npi, rec in agg.items():
        w.writerow([npi, rec[0], f"{rec[1]:.2f}", f"{rec[2]:.2f}",
                    f"{rec[3]:.2f}", f"{rec[4]:.2f}", rec[5]])

sys.stderr.write(f"DONE. rows={total_rows:,} NPIs={len(agg):,} "
                 f"elapsed={time.time()-t0:.1f}s\n")
