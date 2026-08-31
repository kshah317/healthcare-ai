# Clinical Trial Eligibility Criteria Structurer

Every clinical trial posts a paragraph explaining who's allowed to join, called the "eligibility criteria." I built a tool that reads that paragraph and turns it into clean data: what age range qualifies, what sex is required, and a categorized list of every rule and why it's there.

## Why I built this

Each trial's eligibility paragraph is written by a different research team, in a different style. Some number the rules, some bullet them, some just write full paragraphs with no formatting at all. If you're trying to figure out which trials someone qualifies for, or comparing eligibility across dozens of trials, you end up reading everything by hand. There are roughly half a million trials registered on ClinicalTrials.gov, so that reading adds up fast. I wanted to see how much of that I could automate with nothing but pattern matching.

## What it does

Feed it a trial's eligibility text, and you get back:

* a normalized age range in years (handles "18-65 years," "aged 18 to 75," and "65 years of age" the same way)
* a sex requirement, figured out even when it's only implied, like "postmenopausal women"
* every inclusion and exclusion rule, split out and labeled (pregnancy, lab results, prior treatment, etc.) so you can skim straight to what matters to you

## How it works

This is basically three small text-understanding jobs stitched together: finding specific facts in a sentence (like an age or a sex requirement), splitting a document into its "who's allowed in" and "who's kept out" halves, and catching negative phrasing, like recognizing that "no history of seizures" is a rule about someone *not* having seizures, not a rule about having them. I wrote all three by hand using regular expressions (pattern-matching rules for text) instead of reaching for an off-the-shelf AI library, so every decision the tool makes is something I can point to and explain.

I stuck to Python's built-in tools only, nothing installed. No spaCy, no NLTK, no machine learning model.That was a deliberate choice. If a tool tells you a trial excludes women, or requires patients over 65, you should be able to see exactly why it decided that. Hand-written rules are fully readable, anyone can trace an answer back to the exact line of logic that produced it. A trained model might handle messy phrasing better, but you lose that transparency, and for something touching health decisions, I'd rather have a tool that's explainable than one that's just "usually right."

## Evaluation

I didn't have to manually check any of this. Every trial on ClinicalTrials.gov already comes with two versions of the same information: the messy paragraph I'm parsing, and separate, clean fields (age, sex) that the registry fills in itself when a trial gets registered. I used that clean version as the answer key and checked my parser's output against it automatically. The bundled sample data covers 14 real trials across six conditions (diabetes, breast cancer, depression, asthma, hypertension, epilepsy), so the whole thing runs and grades itself with zero setup.

## Results

* Sex: 14/14 correct
* Minimum age: 12/14 correct
* Maximum age: 7/8 correct (only 8 of the 14 trials list an upper age limit at all)

The two age misses aren't the parser being sloppy. In both cases, the registry's clean age field simply isn't repeated anywhere in the actual paragraph, so there's nothing in the text to find. The tool reports this honestly every time you run the accuracy check instead of hiding it.

## Structure

```
clinical-nlp/
README.md
models.py           <- CriterionItem and StructuredCriteria, the shared output shapes
criteria_parser.py  <- the parser: sections, bullets, age, sex, category, negation
fetch_trials.py     <- live ClinicalTrials.gov API client
cli.py               <- menu driven demo
tests.py             <- test suite, including the self-check
data/
    sample_trials.json  <- 14 real, bundled trials for offline use
```

## Run it

```bash
python cli.py
```

Pick a bundled trial to see it structured, run the accuracy check, fetch live trials for any condition (needs internet), or paste in your own eligibility text.

```bash
python -m unittest tests.py -v
```

## Limitations

This is a personal project, not a medical tool. The rules were tuned on 14 real trials across six conditions, so unfamiliar phrasing will trip it up. If a detail only lives in the registry's clean metadata and is never actually written out in the paragraph, no text-reading tool can recover it. Categories come from a fixed list of keywords rather than a trained model, so an unusual sentence can land in the catch-all "other" bucket. None of this should be used to make actual enrollment decisions.
