# Methodology notes

## Sample sizes and effect sizes

All five research questions exceed their minimum required sample sizes
computed via Cohen (1988) conventions (α = .05, power = 0.80, medium
effects). Achieved n's range from 3,265 (RQ4) to 995,954 (RQ2/RQ5),
exceeding their respective minima by factors of 7x to 1,775x.

## RQ5 substitutable-pair cost differential

The headline brand-vs-generic cost differential of $946/claim that
appears in many policy reports is inflated by ultra-specialty brand drugs
(biologics, orphan drugs) that have no generic equivalents. To produce a
realistic savings estimate, this analysis identifies the 368 generic-name
groups in the CMS Drug Spending file where both a brand and a generic
version appear, then computes the claim-weighted cost-per-claim
differential across those substitutable pairs only. The result is
$316.86/claim, which is the figure used in RQ5.

## State demographics

BRFSS and ACS state-level demographic values were transcribed from the
published CDC Prevalence & Trends data (2023) and Census ACS 2019-2023
5-Year Estimates. The seven predictors used in the RQ2 OLS are:

1. age65_pct, ACS 2023 5Y
2. diabetes_pct, BRFSS 2023 age-adjusted
3. htn_pct, BRFSS 2023
4. obesity_pct, BRFSS 2023
5. median_hh_inc, ACS 2023 5Y (rescaled to per $10K in the regression)
6. uninsured_pct, ACS 2023 5Y for adults 19-64
7. college_pct, ACS 2023 5Y for adults 25+
