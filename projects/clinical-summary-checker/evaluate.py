# evaluate.py
#
# two tests. first, planted errors: take faithful summaries, plant one known false claim, and
# see how often the checker flags it (recall), plus how often it flags the untouched faithful
# summaries (false alarms). second, a model run: have the summarizer write summaries of every
# note and report how many contain a claim the note does not back up.
#
# usage: python evaluate.py --model mock|qwen

import argparse
import json

from checker import check_summary, unsupported
from notes import NOTES, gold_summary
from plant import KINDS, plant


def planted_eval(seed=0):
    results = {k: {"planted": 0, "caught": 0} for k in KINDS}
    false_alarms = 0

    for note in NOTES:
        # the untouched faithful summary should raise nothing
        if unsupported(check_summary(note["text"], gold_summary(note))):
            false_alarms += 1

        for kind in KINDS:
            planted = plant(note, kind, seed)
            # skip notes that have nothing to build this error from
            if planted is None:
                continue
            summary, key = planted
            flagged = unsupported(check_summary(note["text"], summary))
            results[kind]["planted"] += 1

            # a catch counts only if the flagged claim is the planted one
            if any(key.lower() in c.text.lower() for c in flagged):
                results[kind]["caught"] += 1

    return results, false_alarms


def model_eval(summarizer):
    rows = []
    for note in NOTES:
        summary = summarizer.summarize(note["text"])
        flagged = unsupported(check_summary(note["text"], summary))
        rows.append({
            "id": note["id"],
            "summary": summary,
            "flagged": [{"kind": c.kind, "text": c.text, "reason": c.reason} for c in flagged],
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["mock", "qwen"], default="mock")
    parser.add_argument("--out", default="results.json")
    args = parser.parse_args()

    results, false_alarms = planted_eval()
    total = sum(r["planted"] for r in results.values())
    caught = sum(r["caught"] for r in results.values())

    print("planted errors")
    for kind, r in results.items():
        print(f"  {kind:22s} caught {r['caught']} of {r['planted']}")
    print(f"  overall: {caught} of {total} caught")
    print(f"  false alarms on faithful summaries: {false_alarms} of {len(NOTES)}")

    if args.model == "qwen":
        from summarizer import HFSummarizer
        summarizer = HFSummarizer()
    else:
        from summarizer import MockSummarizer
        summarizer = MockSummarizer(NOTES)

    rows = model_eval(summarizer)
    with_flags = [r for r in rows if r["flagged"]]
    print(f"\n{args.model} summaries with at least one unsupported claim: {len(with_flags)} of {len(rows)}")
    for r in with_flags:
        print(f"  {r['id']}: {[(c['kind'], c['text']) for c in r['flagged']]}")

    with open(args.out, "w") as f:
        json.dump({"model": args.model, "planted": results, "false_alarms": false_alarms, "summaries": rows}, f, indent=2)


if __name__ == "__main__":
    main()
