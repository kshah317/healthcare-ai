# Patient Readmission Predictor

A machine learning model that scores a diabetic patient's risk of being readmitted to the hospital within 30 days of discharge, using only the kind of data a hospital already has on hand at discharge time.

## Why I built this

I wanted a healthcare project that deals with real financial stakes, not just clinical curiosity. Hospitals actually get penalized by Medicare when too many of their patients bounce back within 30 days. That penalty is real money, and it comes from something a good model might catch early. I wanted to see how far a fairly simple, honest model could get on this exact problem, and I wanted to be upfront about where it fails, not just where it succeeds.

I also wanted this project to reflect something I care about outside of the model itself. A hospital risk score isn't just a number. It can quietly treat one group of patients worse than another, even if nobody intended that. So this project doesn't stop at "does it work." It also checks whether it works equally well for everyone.

## Which dataset, and why

I used the UCI "Diabetes 130-US Hospitals for Years 1999-2008" dataset. It comes from a real 2014 clinical study and contains 101,766 real inpatient hospital encounters across 130 US hospitals, all involving patients diagnosed with diabetes.

I picked this dataset for a few clear reasons. It is real hospital data, not something simulated. It already contains exactly the fields this problem needs: age, diagnosis codes, number of lab procedures, number of medications, and prior visit history. It is freely licensed, so I can point directly to the source instead of describing a vague or private dataset. And it includes race and gender, which is what makes an honest fairness check possible at all.

## What it does

At its core, this project trains a model that looks at a patient's information at the moment of discharge and outputs one number: the probability that this patient will be back in the hospital within 30 days. A hospital could use a score like this to decide who gets a follow-up phone call, a home health referral, or closer attention before they walk out the door.

## Real world impact

This isn't a made-up scenario. Since 2012, Medicare's Hospital Readmissions Reduction Program has penalized hospitals up to 3 percent of their entire Medicare payments, not just the readmission cases, if their 30-day readmission rates are too high. In fiscal year 2026, roughly 2,545 of the 3,400 hospitals subject to this program, about 75 percent, are being penalized, with a typical penalty around 0.69 percent of their Medicare reimbursement. For a hospital already running on thin margins, that adds up fast.

The clinical side matters just as much as the financial side. A 30-day readmission often means something went wrong after discharge: unclear instructions, a missed follow-up appointment, a complication nobody caught in time. A risk score does not fix any of that by itself. What it does is tell a care team where to point their limited follow-up time, toward the patients who actually need it, instead of spreading that attention thin across everyone equally.

## How I built it

A few choices mattered enough that I want to explain them directly.

I removed every encounter where the patient died or was discharged to hospice. A patient who died cannot be readmitted, so leaving those rows in would let the model learn from outcomes that were never actually possible. That is a classic form of data leakage, and catching it before training matters more than any modeling choice that comes after it.

I split the data by patient, not by row. The same patient can appear in this dataset more than once, since they may have been admitted multiple times over the ten years. If the same patient ended up in both the training set and the test set, the model could partly recognize them instead of genuinely generalizing to a new person. So every patient's encounters go entirely into either the training set or the test set, never both.

I grouped the raw diagnosis codes into a small number of clinical categories, like circulatory, respiratory, or diabetes, instead of feeding in hundreds of raw numeric codes directly. Those raw codes on their own carry no meaning to a model.

I deliberately did not give the model race or gender as inputs. A hospital risk score should not price a patient's risk differently because of their race. But leaving those fields out of training does not automatically make a model fair, since other features can still correlate with them. So instead, I use race and gender only afterward, to check whether the model's mistakes land unevenly across those groups even without ever seeing them directly.

Only about 11 percent of encounters in this dataset are an actual 30-day readmission. A model that always guessed "no" would be right 89 percent of the time and still be completely useless. So I never report plain accuracy as a real result. I report ROC-AUC and PR-AUC instead, which are built specifically to handle a rare outcome like this one honestly.

## Results

I trained two models on the same cleaned data and the same held-out test set, so the comparison between them is fair.

| Model | ROC-AUC | PR-AUC |
|---|---|---|
| Logistic regression | 0.664 | 0.219 |
| Gradient boosted trees | 0.667 | 0.225 |

Both numbers sit comfortably above 0.5, meaning both models are doing real work, not guessing. Neither model is dramatically better than the other here, the gradient boosted model edges ahead slightly, but not enough to say the extra complexity clearly pays off on this dataset. Given that, the logistic regression is the more honest headline result: it is nearly as accurate, and every one of its decisions can be traced back to a specific, explainable coefficient.

Out of 101,766 total encounters, removing the expired and hospice cases left 99,343 clean rows, split into 79,541 for training and 19,802 for testing.

## Fairness audit

This is the part of the project I think matters most. I checked the gradient boosted model's false negative rate, the rate at which it misses a patient who really was readmitted, broken down by race and gender. A false negative here is the dangerous kind of error, since it means a patient who needed follow-up care did not get flagged for it.

| Race | Patients in test set | False negative rate | Recall |
|---|---|---|---|
| Caucasian | 14,886 | 41.3% | 58.7% |
| African American | 3,707 | 44.7% | 55.3% |
| Hispanic | 371 | 46.2% | 53.8% |
| Other | 298 | 50.0% | 50.0% |
| Asian | 122 | 40.0% | 60.0% |

| Gender | Patients in test set | False negative rate | Recall |
|---|---|---|---|
| Female | 10,645 | 39.9% | 60.1% |
| Male | 9,157 | 45.3% | 54.7% |

The model misses more true readmissions among African American patients than Caucasian patients, and more among male patients than female patients, even though it was never told either attribute directly. That's the proxy effect I mentioned above: other features the model does use apparently correlate enough with race and gender to reproduce some of that gap anyway. The smallest groups, Asian and Other, have too few patients here to draw a strong conclusion from, their numbers can swing a lot from a handful of cases either way. But the Caucasian versus African American gap involves large enough groups on both sides that it looks real, not noise, and it's exactly the kind of finding a hospital would need to know about before trusting this model to guide who gets follow-up care.

## Data

The raw data is not bundled in this repository, since it is about 18 megabytes. Instead, `fetch_data.py` downloads it directly from the UCI Machine Learning Repository the first time you run the project. The dataset is licensed under CC BY 4.0, which permits this, and the underlying study is:

Beata Strack, Jonathan P. DeShazo, Chris Gennings, Juan L. Olmo, Sebastian Ventura, Krzysztof J. Cios, and John N. Clore, ["Impact of HbA1c Measurement on Hospital Readmission Rates: Analysis of 70,000 Clinical Database Patient Records,"](https://www.hindawi.com/journals/bmri/2014/781670/) BioMed Research International, vol. 2014, Article ID 781670, 2014.

## Structure

```
readmission-predictor/
README.md
fetch_data.py       <- downloads the raw dataset from UCI, stdlib only
preprocess.py         <- cleaning, leakage removal, diagnosis bucketing, patient-level split
model.py               <- the two sklearn pipelines: logistic regression and gradient boosting
fairness_audit.py       <- subgroup false negative/false positive rate breakdown
cli.py                   <- menu driven demo tying everything together
tests.py                  <- unit tests, offline by default
```

## Run it

```bash
python cli.py
```

The first run downloads the dataset automatically. From the menu you can train and compare both models, see the full confusion matrix and classification report, run the fairness audit, or score a made-up patient at discharge.

```bash
python -m unittest tests.py -v
```

## Limitations

This model only says who is at risk, it does not say why, and it does not fix anything by itself. A hospital would still need an actual follow-up program behind it for a risk score to translate into fewer readmissions. The dataset is also over a decade old, from 1999 to 2008, so it reflects how diabetes was treated then, not necessarily how it's treated today. And as the fairness audit shows plainly, this model performs meaningfully worse for some groups of patients than others, which means it should not be deployed as-is without addressing that gap first.
