# QM 640 Capstone — Medicare Part D Drug Spending Analysis

**Author:** Angel Pena
**Institution:** Walsh College, QM 640 Data Analytics Capstone
**Instructor:** Dr. Sanhita Karmakar
**Term:** Spring 2026

## Project summary

This project examines Medicare Part D drug spending across 2013-2023 using
publicly available CMS administrative data, plus the CMS Open Payments 2023
General Payments file and state-level demographics from CDC BRFSS and U.S.
Census Bureau ACS 5-Year Estimates. The project answers five research
questions:

- **RQ1.** What drug attributes are statistically significant predictors of
  total spending growth from 2019 to 2023? (OLS multiple regression with
  5-fold cross-validation.)
- **RQ2.** Are there significant state-level variations in brand-versus-generic
  prescribing rates, and what demographic factors predict higher brand
  utilization? (One-way ANOVA plus multivariable OLS with BRFSS+ACS
  demographics.)
- **RQ3.** Does the presence of Open Payments financial relationships correlate
  with higher-cost prescribing? (Within-specialty logistic regression on the
  NPI-matched Open Payments file.)
- **RQ4.** Can unsupervised clustering identify distinct drug utilization
  profiles? (K-means with k=4 and the elbow method.)
- **RQ5.** What is the estimated annual savings opportunity if high-cost
  prescribers shifted brand-to-generic ratios to match the median in their
  specialty? (Counterfactual simulation with 1,000-iteration bootstrap CI and
  a substitution-rate sensitivity sweep.)

## Headline findings

- RQ1 OLS: R² = 0.920 in-sample, 0.918 cross-validated (no overfitting).
- RQ2 state ANOVA: F = 179.5, η² = 0.0095. State as a factor explains ~1%
  of variance. RQ2 OLS with BRFSS+ACS demographics: R² = 0.61.
- RQ3 logistic on 650,861 prescribers: total payment exposure OR = 1.035,
  speaker fees OR = 1.024, large $1,000+ payments OR = 1.094, food-and-
  beverage alone OR = 0.949 (negative).
- RQ4: four interpretable drug clusters; High-Spend High-Growth (845 drugs)
  is the formulary target, anchored by Eliquis, Ozempic, Jardiance,
  Trulicity, and Mounjaro.
- RQ5: floor estimate $9.91B/year (95% CI $9.59B-$10.26B at 50%
  substitution per Choudhry et al. 2011), ceiling $19.83B.

## Repository structure

```
.
├── README.md
├── requirements.txt
├── .gitignore
├── download_data.sh           script that downloads the raw CMS+OP files
├── src/                       all analysis and report-builder code
├── data/                      CSV outputs (small files only)
├── figures/                   PNG outputs from analysis_v3.py
├── reports/                   final PDF, DOCX, PPTX, Q&A prep
└── docs/                      methodology notes
```

## Running the analysis

```bash
# 1. Install dependencies
pip install -r requirements.txt
npm install -g pptxgenjs

# 2. Download raw CMS + Open Payments data (~12 GB)
bash download_data.sh

# 3. Run the analysis pipeline
python src/analysis_v3.py
python src/full_prescriber_aggregate.py
python src/rq2_full_anova.py
python src/rq2_brfss_ols.py
python src/rq3_full_specialty_anova.py
python src/op_aggregate_arrow.py "$DL/Final Submission/data/open_payments_npi_summary.csv"
python src/rq3_logistic.py
python src/rq5_full_savings_v2.py
python src/rq1_kfold_cv.py

# 4. Build the deliverables
python src/build_report_v5.py    # PDF
python src/build_docx_v5.py      # DOCX
node   src/build_pptx_v2.js      # PPTX
python src/build_qa_prep_v2.py   # Q&A prep
```

## Data sources

- **CMS Part D Grand Totals by Calendar Year (2013-2023)** —
  https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers
- **CMS Part D Spending by Drug (2019-2023)** —
  https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicare-part-d-spending-by-drug
- **CMS Part D Prescribers, by Provider and Drug (2023)** —
  https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug
- **CMS Open Payments 2023 General Payments** —
  https://www.cms.gov/openpayments
- **CDC BRFSS Prevalence & Trends Data (2023)** —
  https://www.cdc.gov/brfss/brfssprevalence/
- **U.S. Census Bureau American Community Survey 2019-2023 5-Year Estimates** —
  https://www.census.gov/programs-surveys/acs/


