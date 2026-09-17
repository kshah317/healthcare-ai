# Healthcare AI

Applied ML/NLP projects at the intersection of clinical data and imaging informatics. 

**Suggested GitHub topics:** `healthcare-ai` `clinical-nlp` `medical-imaging` `machine-learning` `rlhf` `python`

## Structure

Each subfolder under `projects/` is a self-contained project with its own README.

```
healthcare-ai/
README.md                    <- you are here (overview + links to each project)
projects/
  imaging-informatics/       <- e.g. image preprocessing, classification, segmentation work
  clinical-nlp/               <- e.g. clinical note structuring, entity extraction, de-identification
  rlhf-clinical-alignment/    <- flagship: RLHF-style alignment applied to clinically cautious language
  readmission-predictor/     <- predicts 30-day hospital readmission risk, with a race/gender fairness audit
```

## Projects

| Project | Description | Stack |
|---|---|---|
| [rlhf-clinical-alignment](projects/rlhf-clinical-alignment) | Flagship — RLHF-style pipeline aligning a small model toward clinically cautious language | |
| [imaging-informatics](projects/imaging-informatics) | *placeholder — describe once populated* | |
| [clinical-nlp](projects/clinical-nlp) | Rule-based parser that structures free-text clinical trial eligibility criteria into normalized age, sex, and categorized inclusion/exclusion bullets, self-validated against ClinicalTrials.gov's own structured fields | Python (stdlib only) |
| [readmission-predictor](projects/readmission-predictor) | Predicts whether a diabetic patient will be readmitted within 30 days of discharge, using logistic regression and gradient boosting, with a post-hoc fairness audit by race and gender | Python, scikit-learn, pandas |

## Notes on data

Any clinical or imaging data used is public/de-identified benchmark datasets (e.g. MIMIC-III/IV with proper credentialing, NIH ChestX-ray14, i2b2/n2c2 shared task corpora). No real patient data, even anonymized-looking samples, committed without confirming the dataset's redistribution license explicitly permits it.
