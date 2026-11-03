# Clinical Summary Checker

I wanted to see how often a small AI model makes things up when it summarizes a medical note, and whether a simple checker can catch it.

So I wrote 20 fake clinical notes (none of these people exist), had a small open model (Qwen2.5-0.5B-Instruct) summarize each one, and built a checker that reads the summary and asks "does the note actually say this?" for every drug, dose, condition, allergy and number it finds.

## How it works

1. `notes.py` has the 20 made-up notes, plus a list of the true facts in each one.
2. `summarizer.py` runs Qwen on a note and returns its summary.
3. `checker.py` pulls the claims out of the summary and looks each one up in the note. Anything the note doesn't back up gets flagged. It's plain pattern matching, no second AI, so it's easy to read and to test.
4. `plant.py` takes a correct summary and slips in one known mistake (a made-up drug, a doubled dose, a condition the note ruled out, and so on). That way I know exactly what the checker should catch.
5. `evaluate.py` runs both tests and prints the numbers.

## Results

Run on a Colab T4 GPU. Numbers are from the actual run.

**Planted mistakes.** I planted 148 mistakes across 8 types. The checker caught 111.

| Type of mistake | Caught |
|---|---|
| Made-up drug | 20 of 20 |
| Wrong dose | 20 of 20 |
| Made-up condition | 20 of 20 |
| Condition the note ruled out | 14 of 14 |
| Made-up allergy | 20 of 20 |
| Wrong lab value | 17 of 17 |
| Brand-name drug (like "Lipitor") | 0 of 20 |
| Wrong value that matches another number in the note | 0 of 17 |

On the 20 correct summaries it raised no false alarms. The last two rows are on purpose: I built them to be hard, to show where the checker gives up.

**What Qwen actually did.** The first time through, the checker flagged 3 of the 20 summaries, and all 3 were my checker's mistakes, not Qwen's. It misread "allergic reaction to latex" as an allergy called "reaction to latex", and it lost track of a "does not have a history of" when the condition was followed by a bracketed abbreviation. I fixed both, added a check for summaries that say "no allergies" when the note lists one, and ran it again. This time it flagged 1 of 20, and that one is real: Qwen wrote that the patient has no known allergies to sulfa drugs, but the note says she is allergic to sulfa.

Then I read all 20 summaries myself. I found 9 with something wrong, so the checker caught 1 of 9. Here's what it missed:

- Invented treatments or events, like "prescribed oxygen therapy" and "prescribed potassium supplementation" when the note only gave a reading
- A wrong frequency ("metoprolol 50 mg/2 days" for twice daily)
- A drug that was never in the note (sodium nitroprusside)
- A made-up timeline ("improvement in mood after six weeks" when the note said follow up in six weeks)
- Nonsense reasoning ("heart rate 72, indicating no known drug allergies")

## Where it falls short

It only looks at drugs, doses, conditions, allergies and numbers, so anything outside those slips through. It only knows the drug names on its list (plus a few drug-like word endings), so a brand name or an odd drug gets past it. And a wrong number passes if the same number shows up anywhere else in the note.

Also, I added the "no allergies" check after seeing these results, and 20 notes is a small sample. Treat these numbers as a demo of the idea, not a benchmark. The honest takeaway for me: catching planted mistakes is easy, catching what a model really gets wrong is a lot harder.

## Run it

```
pip install -r requirements.txt
python -m unittest tests -v
python evaluate.py --model mock
python evaluate.py --model qwen
```

`--model mock` uses a stand-in summarizer so it runs anywhere with no GPU. Its output is only for testing the pipeline, never a model result. `--model qwen` downloads the model and works best on a GPU.
