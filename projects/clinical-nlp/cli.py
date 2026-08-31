import json
import os

import criteria_parser as parser
import fetch_trials

# menu driven demo for the eligibility criteria structurer, this is the
# entry point meant to be run directly: python cli.py

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "sample_trials.json")


def load_sample_trials():
    # reads the bundled sample data so the tool works fully offline,
    # every option below except "fetch live trials" only needs this file
    with open(DATA_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def print_structured(record: dict):
    # runs one raw trial record through the parser and prints a readable report
    structured = parser.parse_trial(record)
    print("\n" + structured.summary())
    print("\nconditions:", ", ".join(structured.conditions) or "not specified")

    print("\ninclusion criteria:")
    for item in structured.inclusion:
        flag = " [negated]" if item.negated else ""
        print(f"  - ({item.category}){flag} {item.text}")

    print("\nexclusion criteria:")
    for item in structured.exclusion:
        flag = " [negated]" if item.negated else ""
        print(f"  - ({item.category}){flag} {item.text}")


def show_one_sample():
    # lets the user pick a bundled trial by number and see it structured
    trials = load_sample_trials()
    for i, trial in enumerate(trials, start=1):
        print(f"{i}. {trial['nct_id']} - {trial['title']}")
    choice = input("\npick a number: ").strip()
    try:
        index = int(choice) - 1
        print_structured(trials[index])
    except (ValueError, IndexError):
        print("not a valid choice")


def run_accuracy_check():
    # the self evaluation step: compares what the parser extracted against
    # the sex/age fields ClinicalTrials.gov already stores in structured
    # form for the same trial, so accuracy can be measured without anyone
    # hand labeling a single example
    trials = load_sample_trials()
    lo_correct = lo_total = hi_correct = hi_total = sex_correct = 0

    for trial in trials:
        structured = parser.parse_trial(trial)

        known_lo = trial.get("known_minimum_age")
        known_hi = trial.get("known_maximum_age")
        known_lo_years = float(known_lo.split()[0]) if known_lo else None
        known_hi_years = float(known_hi.split()[0]) if known_hi else None

        if known_lo_years is not None:
            lo_total += 1
            lo_correct += structured.minimum_age_years == known_lo_years
        if known_hi_years is not None:
            hi_total += 1
            hi_correct += structured.maximum_age_years == known_hi_years
        sex_correct += structured.sex == trial.get("known_sex")

    print(f"\nminimum age match: {lo_correct}/{lo_total}")
    print(f"maximum age match: {hi_correct}/{hi_total}")
    print(f"sex match: {sex_correct}/{len(trials)}")
    print("\n(mismatches are usually cases where the age lives only in the")
    print("registry's structured field and is never actually stated in the")
    print("free text criteria, a real limitation of any free text parser)")


def fetch_and_structure():
    # exercises the live network path, requires internet access on the
    # machine running this, unlike every other menu option
    condition = input("condition to search (e.g. asthma): ").strip() or "asthma"
    try:
        trials = fetch_trials.fetch_trials(condition, page_size=5)
    except RuntimeError as error:
        print(f"\n{error}")
        return
    for trial in trials:
        print_structured(trial)


def structure_custom_text():
    # freeform mode, paste any eligibility criteria text and see it
    # structured, useful for trying text that never came from a trial at all
    print("paste eligibility criteria text, then press enter twice:")
    lines = []
    while True:
        line = input()
        if line == "" and (not lines or lines[-1] == ""):
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    fake_record = {"nct_id": "CUSTOM", "title": "", "conditions": [], "eligibility_text": text}
    print_structured(fake_record)


def main():
    menu = {
        "1": ("view a bundled sample trial, structured", show_one_sample),
        "2": ("run the accuracy self check against known trial metadata", run_accuracy_check),
        "3": ("fetch live trials from clinicaltrials.gov and structure them", fetch_and_structure),
        "4": ("structure your own pasted eligibility text", structure_custom_text),
    }

    while True:
        print("\nclinical trial eligibility structurer")
        for key, (label, _) in menu.items():
            print(f"  {key}. {label}")
        print("  5. quit")

        choice = input("> ").strip()
        if choice == "5":
            break
        action = menu.get(choice)
        if action:
            action[1]()
        else:
            print("not a valid choice")


if __name__ == "__main__":
    main()
