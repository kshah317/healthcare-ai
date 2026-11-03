# plant.py
#
# plants one known false claim into a faithful summary, so i know exactly what the checker
# should catch. each planter returns (new_summary, key) where key is a lowercase piece of text
# that must show up in a flagged claim for the catch to count. returns None when a note has
# nothing to build that kind of error from.

import random
import re

from notes import gold_summary
from vocab import CONDITIONS

# drugs and allergens used for planting. the drug list is generic names the checker knows.
FAKE_DRUGS = ["warfarin", "digoxin", "prednisone", "sertraline", "allopurinol", "methotrexate"]
FAKE_ALLERGENS = ["latex", "codeine", "shellfish", "aspirin", "iodine"]

# the first six are errors i expect the checker to catch. the last two are built to be hard:
# a brand name the drug list does not know, and a wrong value that matches some other number
# in the note. they show where the checker falls short.
KINDS = [
    "fake_drug", "wrong_dose", "fake_condition", "ruled_out_condition", "fake_allergy",
    "wrong_number", "brand_name_drug", "number_from_elsewhere",
]
BRAND_DRUGS = ["coumadin", "zoloft", "lipitor", "xarelto"]


def _in_note(note, word):
    return re.search(r"\b" + re.escape(word) + r"\b", note["text"].lower()) is not None


def fake_drug(note, rng):
    options = [d for d in FAKE_DRUGS if not _in_note(note, d)]
    if not options:
        return None
    drug = rng.choice(options)
    return gold_summary(note) + f" Also takes {drug} 5 mg.", drug


def wrong_dose(note, rng):
    if not note["meds"]:
        return None
    drug, dose = rng.choice(note["meds"])
    value, unit = dose.split()
    new_value = str(int(float(value) * 2))
    summary = gold_summary(note)
    old = f"{drug} {dose}"
    new = f"{drug} {new_value} {unit}"
    if old not in summary:
        return None
    return summary.replace(old, new), new


def fake_condition(note, rng):
    text = note["text"].lower()
    options = [
        c for c in CONDITIONS
        if not any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in CONDITIONS[c])
    ]
    # skip the general word "diabetes" so the planted error is not a parent of a real one
    options = [c for c in options if c != "diabetes"]
    if not options:
        return None
    cond = rng.choice(options)
    return gold_summary(note) + f" History of {cond}.", cond


def ruled_out_condition(note, rng):
    if not note["negated"]:
        return None
    cond = rng.choice(note["negated"])
    return gold_summary(note) + f" History of {cond}.", cond


def fake_allergy(note, rng):
    options = [a for a in FAKE_ALLERGENS if not _in_note(note, a)]
    if not options:
        return None
    allergen = rng.choice(options)
    return gold_summary(note) + f" Allergic to {allergen}.", allergen


def wrong_number(note, rng):
    if not note["labs"]:
        return None
    name, value, unit = rng.choice(note["labs"])
    summary = gold_summary(note)
    # shift the value by 7, and skip it if that lands on a number already in the note
    shifted = float(value.split("/")[0]) + 7
    new_value = str(int(shifted)) if "." not in value else f"{shifted:.1f}"
    if "/" in value:
        new_value = f"{int(shifted)}/{value.split('/')[1]}"
    if new_value in note["text"]:
        return None
    old = f"{name} {value}"
    if old.lower() not in summary.lower():
        return None
    start = summary.lower().index(old.lower())
    new_summary = summary[:start] + f"{name} {new_value}" + summary[start + len(old):]
    return new_summary, new_value


def brand_name_drug(note, rng):
    options = [b for b in BRAND_DRUGS if not _in_note(note, b)]
    if not options:
        return None
    brand = rng.choice(options)
    return gold_summary(note) + f" Also takes {brand}.", brand


def number_from_elsewhere(note, rng):
    # swap a lab value for the patient's age, which is a number the note really contains
    if not note["labs"]:
        return None
    name, value, unit = note["labs"][0]
    if "/" in value or str(note["age"]) == value:
        return None
    summary = gold_summary(note)
    old = f"{name} {value}"
    if old.lower() not in summary.lower():
        return None
    start = summary.lower().index(old.lower())
    new = f"{name} {note['age']}"
    return summary[:start] + new + summary[start + len(old):], f"{name} {note['age']}"


PLANTERS = {
    "fake_drug": fake_drug,
    "wrong_dose": wrong_dose,
    "fake_condition": fake_condition,
    "ruled_out_condition": ruled_out_condition,
    "fake_allergy": fake_allergy,
    "wrong_number": wrong_number,
    "brand_name_drug": brand_name_drug,
    "number_from_elsewhere": number_from_elsewhere,
}


def plant(note, kind, seed=0):
    # seeded so every run plants the same errors
    rng = random.Random(f"{seed}-{note['id']}-{kind}")
    return PLANTERS[kind](note, rng)
