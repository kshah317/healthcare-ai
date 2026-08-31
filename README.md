# Healthcare AI

Applied ML/NLP projects at the intersection of clinical data and imaging informatics. This is intended as the flagship repo of the portfolio — the one place worth spending the most polish.

**Suggested GitHub topics:** `healthcare-ai` `clinical-nlp` `medical-imaging` `machine-learning` `rlhf` `python`

## Structure

Each subfolder under `projects/` is a self-contained project with its own README, so a visitor can go straight to what interests them.

```
healthcare-ai/
README.md                    <- you are here (overview + links to each project)
projects/
  imaging-informatics/       <- e.g. image preprocessing, classification, segmentation work
  clinical-nlp/               <- e.g. clinical note structuring, entity extraction, de-identification
  rlhf-clinical-alignment/    <- flagship: RLHF-style alignment applied to clinically cautious language
```

## Projects

| Project | Description | Stack |
|---|---|---|
| [rlhf-clinical-alignment](projects/rlhf-clinical-alignment) | Flagship — RLHF-style pipeline aligning a small model toward clinically cautious language | |
| [imaging-informatics](projects/imaging-informatics) | *placeholder — describe once populated* | |
| [clinical-nlp](projects/clinical-nlp) | Rule-based parser that structures free-text clinical trial eligibility criteria into normalized age, sex, and categorized inclusion/exclusion bullets, self-validated against ClinicalTrials.gov's own structured fields | Python (stdlib only) |

## Notes on data

Any clinical or imaging data used is public/de-identified benchmark datasets (e.g. MIMIC-III/IV with proper credentialing, NIH ChestX-ray14, i2b2/n2c2 shared task corpora). No real patient data, even anonymized-looking samples, committed without confirming the dataset's redistribution license explicitly permits it.
