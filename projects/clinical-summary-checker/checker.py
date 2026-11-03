# checker.py
#
# the fact-checker. give it a clinical note and a summary of that note, and it lists the claims
# the summary makes (a drug, a drug with a dose, a condition, an allergy, a number) and says
# whether each one is backed up by the note. anything not backed up is a likely invention.
#
# it works by reading, not by guessing: every claim is found with plain pattern matching and
# then looked up in the note. that keeps it fast, easy to read, and easy to test. the price is
# that it only catches kinds of claims it knows about (see the limits in the README).

import re
from dataclasses import dataclass

from vocab import (
    CONDITIONS,
    DRUG_SUFFIXES,
    DRUGS,
    LAB_NAMES,
    NEGATION_CUES,
    OTHER_PERSON_CUES,
    PARENTS,
)

NUMBER = r"\d+(?:\.\d+)?"

# a dose that sits right after a drug name, like "metformin 500 mg"
DOSE_AFTER = re.compile(rf"^[\s(,:\-]{{0,3}}(?:at\s+)?({NUMBER})\s*(mg|mcg|g|units|iu|ml)\b")

# any dose, anywhere
DOSE_ANYWHERE = re.compile(rf"({NUMBER})\s*(mg|mcg|g|units|iu|ml)\b")

# one condition regex built from every spelling, longest spelling first so that
# "type 2 diabetes mellitus" wins over plain "diabetes"
_SPELLINGS = {}
for _canonical, _words in CONDITIONS.items():
    for _word in _words:
        _SPELLINGS[_word] = _canonical
CONDITION_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(_SPELLINGS, key=len, reverse=True)) + r")\b"
)


@dataclass
class Claim:
    # one thing the summary says, and whether the note backs it up
    kind: str
    text: str
    supported: bool
    reason: str


def _has_word(text, word):
    # true if the word shows up as a whole word
    return re.search(r"\b" + re.escape(word) + r"\b", text) is not None


def _find_drugs(text):
    # returns (word, start, end, known) for every drug name in the text. "known" means the
    # word is on the drug list. otherwise it is a guess based on how the word ends.
    found = []
    for m in re.finditer(r"[a-z][a-z\-]{5,}", text):
        word = m.group(0)

        # a word on the list is a drug for sure
        if word in DRUGS:
            found.append((word, m.start(), m.end(), True))

        # a long word with a drug-like ending is probably a drug
        elif len(word) >= 7 and word.endswith(DRUG_SUFFIXES):
            found.append((word, m.start(), m.end(), False))
    return found


def _doses_in_note(note, drug):
    # every dose the note gives for this drug, as a set of (number, unit)
    doses = set()
    for m in re.finditer(r"\b" + re.escape(drug) + r"\b", note):
        # only look a short way past the drug name so a neighbor's dose is not borrowed
        near = DOSE_ANYWHERE.search(note[m.end(): m.end() + 40])
        if near:
            doses.add((float(near.group(1)), near.group(2)))
    return doses


def _find_conditions(text):
    # returns (standard name, start) for every condition mentioned
    found = []
    for m in CONDITION_RE.finditer(text):
        name = _SPELLINGS[m.group(1)]

        # "chronic obstructive pulmonary disease (copd)" is one mention, not two
        if found and found[-1][0] == name and text[max(0, m.start() - 1): m.start()] == "(":
            continue
        found.append((name, m.start()))
    return found


def _prefix(text, start):
    # the few words before a mention, cut off at the start of the sentence or at "but"
    before = text[max(0, start - 60): start]
    before = re.split(r"[.;\n]", before)[-1]
    before = re.split(r"\b(?:but|however)\b", before)[-1]
    return " ".join(before.split()[-6:])


def _is_negated(text, start):
    # true when the words just before the mention say it is ruled out ("no history of ...")
    return NEGATION_CUES.search(_prefix(text, start)) is not None


def _note_conditions(note):
    # what the note says about each condition: present, ruled out, or both
    present, ruled_out = set(), set()
    for name, start in _find_conditions(note):
        prefix = _prefix(note, start)

        # a relative's condition is not the patient's, so ignore it
        if OTHER_PERSON_CUES.search(prefix):
            continue

        # ruled out versus really there
        if NEGATION_CUES.search(prefix):
            ruled_out.add(name)
        else:
            present.add(name)
    return present, ruled_out


def _overlaps(spans, start, end):
    # true if this stretch of text was already claimed by an earlier check
    return any(start < e and s < end for s, e in spans)


def check_summary(note, summary):
    """returns a list of Claim objects, one for each claim found in the summary."""
    note_l = note.lower()
    text = summary.lower()
    claims = []
    used = []

    # 1. drugs, and the doses that go with them
    for word, start, end, known in _find_drugs(text):
        in_note = _has_word(note_l, word)
        if in_note:
            reason = "this medication is in the note"
        elif known:
            reason = "this medication is not in the note"
        else:
            reason = "this looks like a drug name and is not in the note"
        claims.append(Claim("drug", word, in_note, reason))

        # a dose written right after the drug name
        dose = DOSE_AFTER.search(text[end: end + 25])
        if dose:
            used.append((end + dose.start(1), end + dose.end()))

            # if the drug itself is not in the note, the drug claim already covers it
            if in_note:
                value, unit = float(dose.group(1)), dose.group(2)
                ok = (value, unit) in _doses_in_note(note_l, word)
                label = f"{word} {dose.group(1)} {unit}"
                why = "this dose matches the note" if ok else "the note gives a different dose or none"
                claims.append(Claim("dose", label, ok, why))

    # 2. conditions (a condition the summary says is absent is not a claim, so it is skipped)
    present, ruled_out = _note_conditions(note_l)
    for name, start in _find_conditions(text):
        if _is_negated(text, start):
            continue

        # a general word like "diabetes" is backed up by a specific type in the note
        backers = [name] + PARENTS.get(name, [])
        if any(b in present for b in backers):
            claims.append(Claim("condition", name, True, "this condition is in the note"))
        elif name in ruled_out:
            claims.append(Claim("condition", name, False, "the note says this was ruled out"))
        else:
            claims.append(Claim("condition", name, False, "this condition is not in the note"))

    # 3. allergies
    for m in re.finditer(r"allerg(?:ic|y|ies)(?:\s+to|\s*:)?\s+([^.;]+)", text):
        # "no known allergies" says there are none, so there is nothing to check
        if re.search(r"\bno\b(?:\s+known)?(?:\s+\w+)?\s*$", text[max(0, m.start() - 15): m.start()]):
            continue

        for item in re.split(r",| and ", m.group(1)):
            item = item.strip()

            # "an allergic reaction to latex" is about latex
            item = re.sub(r"^(?:an?\s+)?(?:allergic\s+)?(?:reactions?|sensitivity)\s+to\s+", "", item)

            # skip empty bits and long runs of words that are not an allergen
            if not item or len(item.split()) > 3:
                continue
            ok = re.search(r"allerg[^.]{0,120}" + re.escape(item), note_l) is not None
            reason = "the note lists this allergy" if ok else "the note does not list this allergy"
            claims.append(Claim("allergy", item, ok, reason))

    # a summary that says there are no allergies is wrong if the note lists one
    if re.search(r"\b(?:no|without|denies(?:\s+any)?)\s+(?:known\s+)?(?:drug\s+)?allergies", text):
        has_allergy = re.search(r"allergic to|allergy to", note_l) is not None
        why = "the note lists an allergy" if has_allergy else "the note has no allergies"
        claims.append(Claim("allergy", "no allergies", not has_allergy, why))

    # 4. numbers: age, named lab values, blood pressure, and loose numbers with units
    note_numbers = set(re.findall(rf"{NUMBER}(?:/\d+)?", note_l))

    def add_number(label, value, span):
        # one number claim, backed up if the same number appears anywhere in the note
        used.append(span)
        ok = value in note_numbers
        why = "this number is in the note" if ok else "this number is not in the note"
        claims.append(Claim("number", label, ok, why))

    for m in re.finditer(rf"({NUMBER})[- ]?(?:year|yr)s?[- ]?old", text):
        add_number(f"{m.group(1)} years old", m.group(1), m.span(1))

    for name in LAB_NAMES:
        for m in re.finditer(r"\b" + re.escape(name) + rf"\b\D{{0,15}}?({NUMBER}(?:/\d+)?)", text):
            if not _overlaps(used, *m.span(1)):
                add_number(f"{name} {m.group(1)}", m.group(1), m.span(1))

    for m in re.finditer(r"\b\d{2,3}/\d{2,3}\b", text):
        if not _overlaps(used, *m.span()):
            add_number(m.group(0), m.group(0), m.span())

    loose = rf"({NUMBER})\s*(%|mg/dl|mmol/l|bpm|mmhg|kg|lbs?|cm|g/dl)"
    for m in re.finditer(loose, text):
        if not _overlaps(used, *m.span(1)):
            add_number(f"{m.group(1)} {m.group(2)}", m.group(1), m.span(1))

    # a dose with no recognized drug in front of it still has to be a number from the note
    for m in DOSE_ANYWHERE.finditer(text):
        if not _overlaps(used, *m.span(1)):
            add_number(f"{m.group(1)} {m.group(2)}", m.group(1), m.span(1))

    return claims


def unsupported(claims):
    """the claims the note does not back up."""
    return [c for c in claims if not c.supported]
