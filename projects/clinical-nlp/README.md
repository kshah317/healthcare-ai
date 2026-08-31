# Clinical Trial Eligibility Criteria Structurer

A tool that reads the free text "eligibility criteria" block published with every clinical trial and turns it into structured data: who qualifies by age and sex, and a categorized, bullet by bullet breakdown of why.

## The problem

Every trial on ClinicalTrials.gov publishes its eligibility rules as a wall of unstructured text, written by a different research team, in a different format, every time. Some trials number their criteria, some bullet them, some write them as flowing prose with no punctuation cues at all. A researcher screening patients, a patient search tool, or anyone trying to compare eligibility across many trials at once has to read every single one by hand, because the text was never designed to be queried, filtered, or compared. Multiply that by the roughly half a million trials registered on the platform and it becomes a real bottleneck: valuable structure (who can enroll, why, and under what conditions) is trapped inside prose.

This is a small, honest version of a problem real health informatics teams work on: understanding unstructured clinical text at scale.

## Why this is NLP

The core task is natural language understanding: taking human written text and recovering the structure and meaning underneath it, specifically who a document is describing (an age range, a sex requirement), which sentences are requirements versus disqualifiers, and what each one is actually about (a lab value, a pregnancy exclusion, prior treatment history). That is the same shape of problem as named entity recognition (pulling ages and sex out of a sentence), text segmentation (splitting inclusion from exclusion), and negation detection (a technique from real clinical NLP, generally known as NegEx, that flags phrases like "no history of X" as negative findings rather than positive ones). This project implements light versions of all three, by hand, so the logic stays fully visible.

## What NLP tools are used, and why

Everything here is built on Python's standard library: `re` for pattern matching, `dataclasses` for the structured output shapes, `urllib.request` for pulling live data, and `unittest` for testing. No spaCy, no NLTK, no scikit-learn, no trained model of any kind.

That is a deliberate choice, not a shortcut. Clinical text is exactly the domain where a black box model is a liability: if a tool decides a trial excludes women, or requires patients to be over 65, a person needs to be able to see *why* it decided that. A rule based parser can be read top to bottom, and every extracted field traces back to an exact regular expression a person can inspect and fix. Machine learning approaches to this problem exist and can outperform hand written rules on messier text, but they trade that transparency for accuracy, and in a domain where a wrong eligibility read has real consequences, an auditable "wrong answer" is worth more than an opaque "usually right" one. The tradeoff is spelled out in `criteria_parser.py` directly: every extraction rule sits in one readable function, tuned against real trial text rather than a synthetic example.

## How it eases the underlying problem

Instead of reading a trial's eligibility text end to end, a user (or another piece of software) gets back:

* a normalized minimum and maximum age, in years, regardless of whether the original text said "18-65 years," "aged 18 to 65," "age >= 18 <= 65 years," or "65 years of age"
* a normalized sex requirement (`FEMALE`, `MALE`, or `ALL`), resolved even when the text only implies it through words like "postmenopausal women" while correctly ignoring routine mentions like "pregnant women" in an exclusion list for an otherwise mixed sex trial
* every inclusion and exclusion line split out individually and tagged with a category (pregnancy, prior therapy, lab values, psychiatric history, and so on), so a reader can jump straight to the kind of criterion they care about instead of reading the whole block

That is the same value any structuring pipeline provides: it does not answer clinical questions, it removes the manual reading step so a person (or a downstream tool) can act on the trial faster.

## Data: where the evaluation comes from

The data source is the free, public [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api), no key or account required. `fetch_trials.py` calls it directly and normalizes each result into one flat shape.

The interesting part is how this project evaluates itself without any manual labeling. Every trial record returned by the API already carries two versions of the same fact: the raw free text eligibility criteria (what this project parses), and separate, pre-structured `sex`, `minimumAge`, and `maximumAge` fields that ClinicalTrials.gov extracts itself when a trial is registered. That second set of fields is treated as ground truth, and the parser's output is checked against it automatically. `data/sample_trials.json` bundles 14 real trials, picked to cover the range of formatting styles actually seen in the wild (numbered lists, nested bullets, colon-less headers, unicode comparison symbols, escaped markdown characters), across six different conditions (diabetes, breast cancer, depression, asthma, hypertension, epilepsy), so the project runs and evaluates itself fully offline. Option 3 in the CLI fetches fresh trials live for any condition typed in.

## Results

Run against the bundled sample data, the parser currently gets:

* sex: 14/14 correct (100%)
* minimum age: 12/14 correct (86%)
* maximum age: 7/8 correct (88%, only 8 of the 14 sample trials specify an upper bound at all)

The misses are worth naming rather than hiding: in a couple of sample trials, ClinicalTrials.gov's own structured age field is simply not restated anywhere in the free text criteria, so no text based parser, rule based or otherwise, could recover it. That is a genuine limitation of working from free text alone, and `run_accuracy_check()` in `cli.py` reports it every time it runs, rather than only showing a flattering number.

## Structure

```
clinical-nlp/
README.md
models.py           <- CriterionItem and StructuredCriteria, the shared output shapes
criteria_parser.py  <- the rule based parser: sections, bullets, age, sex, category, negation
fetch_trials.py      <- live ClinicalTrials.gov API v2 client, stdlib only
cli.py               <- menu driven demo
tests.py             <- unittest suite, including the self evaluation check
data/
    sample_trials.json  <- 14 real, bundled trials for fully offline use
```

## Run it

```bash
python cli.py
```

From the menu: view a bundled sample trial structured, run the accuracy self check, fetch live trials for any condition (needs internet access), or paste in your own eligibility text.

To run the tests:

```bash
python -m unittest tests.py -v
```

## Known limitations

This is a portfolio scale demonstration, not a clinical decision tool: the regular expressions were tuned against 14 real trials across six conditions, not the full breadth of phrasing used across every trial ever registered, so accuracy will vary on text that looks very different from the samples. Age or sex information that only exists in a trial's structured metadata and is never restated in the free text criteria cannot be recovered by this or any other free text parser. The categorization lexicon is a fixed keyword list rather than a learned model, so an unusual phrasing can fall through to the generic "other" category. None of this output should be used to make real enrollment decisions.
