# QM 640 - Medicare Part D Drug Spending Analysis (Final Submission)

Walsh College Data Analytics Capstone, Spring 2026.
Angel Pena. Mentor: Dr. Sanhita Karmakar.

## Contents

- `QM640_Final_Report.pdf` / `.docx` - the full final report
- `QM640_Final_Report_Validation.md` - reference and metric validation audit
- `QM640_Final_Presentation.pdf` / `.pptx` - capstone defense deck
- `CHANGELOG.md` - what changed between the interim and final submissions
- `REALITY_BRIDGE.md` - mapping from analysis outputs to report claims
- `reports/` - canonical copies of the PDF and DOCX
- `presentation/` - PPTX files (interim and final)
- `data/` - every CSV produced by the analysis pipeline
- `figures/` - every PNG referenced in the report
- `src/` - all Python and JavaScript code
- `docs/` - README, requirements.txt, download script, validation report

## Running the pipeline

The Python scripts under `src/` resolve their paths relative to the script's
own location. As long as the `src/`, `data/`, `figures/`, and `reports/`
folders sit next to each other inside this `Final Submission Repo/` folder,
running any script with `python src/<script>.py` from the repo root will work
without edits.

```
cd "C:\Users\kraam\Downloads\Final Submission Repo"
python src\rq4_cluster_validation.py
python src\build_docx_template.py
```

To run from a different location, set the FINAL_SUBMISSION_DIR environment
variable to wherever the repo root lives:

```
set FINAL_SUBMISSION_DIR=C:\Users\kraam\Downloads\Final Submission Repo
python src\rq4_cluster_validation.py
```

## Requirements

Python 3.11+ with pandas, numpy, scipy, scikit-learn, statsmodels, pyarrow,
matplotlib, python-docx, and reportlab. See `docs/requirements.txt`.

## Reproducibility

All numbers in the Final Report are read live from CSVs in `data/` at
build time. To regenerate the report from raw CMS data:

1. Re-run the data pipeline (`src/analysis_v3.py` and the RQ-specific
   scripts) against refreshed CMS files
2. Re-run the report builder (`src/build_docx_template.py`)
3. Convert the DOCX to PDF with LibreOffice or Word

The metric validation script (`src/validate_metrics.py`, if present) and
the validation Markdown (`docs/Validation_Report.md`) document the
cross-checks done on the published deliverables.
