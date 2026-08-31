import re
from typing import List, Optional, Tuple

from models import CriterionItem, StructuredCriteria

# this module turns the free text "eligibility criteria" blob that every
# clinical trial is published with into a structured record: who qualifies
# by age and sex, and a categorized, bullet by bullet breakdown of why.
#
# everything here is plain pattern matching over the raw string, there is
# no machine learning model and no external nlp library involved, the
# patterns were built and tuned directly against real ClinicalTrials.gov
# text (see data/sample_trials.json), so they reflect how these documents
# are actually phrased rather than a textbook example.

# a small set of time units the criteria text uses when stating an age,
# used to normalize everything down to a single unit: years
UNIT = r"(?:years?|y|months?|weeks?|days?)"

# a short run of punctuation/whitespace only, used to keep a match tied
# closely to the anchor word ("age") instead of drifting into an unrelated
# number that happens to sit nearby in the same sentence
LEAD = r"^[\s:.,\-]{0,6}"

# phrases that make "women"/"woman" a false signal for a female only trial,
# since routine pregnancy exclusions show up in mixed sex trials too
PREGNANCY_WORDS = r"(?:pregnant|nursing|lactating|breastfeeding|childbearing|breast-feeding)"

# category keyword lexicon, checked top to bottom, first match wins, so the
# more specific categories are listed before the general catch all ones
CATEGORY_KEYWORDS = [
    ("pregnancy", ("pregnan", "lactat", "breastfeed", "nursing", "childbearing")),
    ("psychiatric", ("psychiatric", "depress", "schizophren", "suicid", "mental illness", "psychosis", "psychotic")),
    ("substance_use", ("alcohol", "drug abuse", "substance use", "smoking", "smoker")),
    ("lab_values", ("mg/dl", "mg/ml", "ng/ml", "creatinine", "hemoglobin", "platelet",
                     "bilirubin", "egfr", "hba1c", "white blood cell", "bmi", "kg/m2")),
    ("prior_therapy", ("prior therapy", "prior treatment", "previously treated", "prior chemotherapy",
                        "prior radiation", "concurrent therapy", "concomitant", "prior use of")),
    ("consent", ("informed consent", "consent form", "sign the consent", "able to consent")),
    ("logistics", ("able to", "willing to", "access to", "fluency", "fluent", "language", "travel", "smartphone")),
    ("demographics", ("male", "female", "gender", "sex ")),
    ("age", ("age", "years old", "aged")),
    ("comorbidity", ("history of", "disease", "disorder", "syndrome", "cancer", "diabetes",
                      "hypertension", "infection", "diagnosis of", "diagnosed with")),
]


def _unit_to_years(amount: str, unit: Optional[str]) -> float:
    # normalizes a (number, unit) pair down to a single float in years,
    # defaults to "years" when no unit was captured by the regex
    unit = (unit or "years").lower()
    if unit.startswith("year") or unit == "y":
        multiplier = 1.0
    elif unit.startswith("month"):
        multiplier = 1 / 12
    elif unit.startswith("week"):
        multiplier = 1 / 52
    elif unit.startswith("day"):
        multiplier = 1 / 365
    else:
        multiplier = 1.0
    return round(float(amount) * multiplier, 3)


def _bounds_after(window: str) -> Tuple[Optional[float], Optional[float]]:
    # window is the text immediately following the word "age", covers
    # phrasing like "age >= 18", "age 18-65 years", "age 18 to 75"
    match = re.search(rf"{LEAD}(\d+)\s*-\s*(\d+)\s*({UNIT})?", window, re.I)
    if match:
        return _unit_to_years(match.group(1), match.group(3)), _unit_to_years(match.group(2), match.group(3))

    match = re.search(rf"{LEAD}(?:of\s+)?(\d+)\s+(?:to|and)\s+(\d+)", window, re.I)
    if match:
        return float(match.group(1)), float(match.group(2))

    lower_bound = re.search(rf"{LEAD}>=?\s*(\d+)\s*({UNIT})?", window, re.I)
    if lower_bound:
        lo = _unit_to_years(lower_bound.group(1), lower_bound.group(2))
        # a matching upper bound is allowed to sit a little further out
        # in the same window, e.g. "age >= 18 <= 60 years"
        upper_bound = re.search(rf"<=?\s*(\d+)\s*({UNIT})?", window, re.I)
        hi = _unit_to_years(upper_bound.group(1), upper_bound.group(2)) if upper_bound else None
        return lo, hi

    match = re.search(rf"{LEAD}(\d+)\s+and\s+(?:over|older|above)", window, re.I)
    if match:
        return float(match.group(1)), None

    # a single trailing number right after "age", e.g. "age: 18" or "age 18 months and over"
    match = re.search(rf"{LEAD}(\d+)\s*({UNIT})?\s*(?:and\s+(?:over|older))?$", window, re.I)
    if match:
        return _unit_to_years(match.group(1), match.group(2)), None

    return None, None


def _bounds_before(window: str) -> Tuple[Optional[float], Optional[float]]:
    # window is the text right before the word "age", so the number has to
    # be anchored at the *end* of the window to count, e.g. "8-12 years of age"
    match = re.search(rf"(\d+)\s*-\s*(\d+)\s*{UNIT}\s*(?:of\s+)?$", window, re.I)
    if match:
        return _unit_to_years(match.group(1), "years"), _unit_to_years(match.group(2), "years")

    match = re.search(rf"(\d+)\s*({UNIT})\s*(?:of\s+)?$", window, re.I)
    if match:
        return _unit_to_years(match.group(1), match.group(2)), None

    return None, None


def extract_age_range(text: str) -> Tuple[Optional[float], Optional[float]]:
    # walk every occurrence of the word "age"/"aged" and look just after it,
    # then just before it, the first window that yields a bound wins
    for anchor in re.finditer(r"\bage[sd]?\b", text, re.I):
        lo, hi = _bounds_after(text[anchor.end(): anchor.end() + 40])
        if lo is not None or hi is not None:
            return lo, hi
        lo, hi = _bounds_before(text[max(0, anchor.start() - 30): anchor.start()])
        if lo is not None or hi is not None:
            return lo, hi

    # fallback patterns that carry their own unambiguous marker, so they are
    # safe to run over the whole document even without the word "age" nearby
    match = re.search(rf"(\d+)\s*-\s*(\d+)\s*{UNIT}", text, re.I)
    if match:
        return _unit_to_years(match.group(1), "years"), _unit_to_years(match.group(2), "years")

    match = re.search(r"(\d+)\s+and\s+(?:over|older|above)", text, re.I)
    if match:
        return float(match.group(1)), None

    return None, None


def _women_signal(text: str) -> bool:
    # "women"/"woman" only counts as a female indicator when it is not just
    # part of a routine pregnancy exclusion, since those appear in
    # mixed sex trials too and would otherwise mislabel them as female only
    for match in re.finditer(r"\bwom[ae]n\b", text, re.I):
        nearby = text[max(0, match.start() - 25): match.start()]
        if not re.search(PREGNANCY_WORDS, nearby, re.I):
            return True
    return False


def extract_sex(text: str) -> str:
    # combines a direct "female"/"male" mention with the softer "women"/"men"
    # signal, then resolves the pair down to one of three eligibility values
    has_female = bool(re.search(r"\bfemale", text, re.I)) or _women_signal(text)
    has_male = bool(re.search(r"\bmale\b|\bmen\b", text, re.I))
    if has_female and has_male:
        return "ALL"
    if has_female:
        return "FEMALE"
    if has_male:
        return "MALE"
    return "ALL"  # unspecified defaults to open to everyone


def split_sections(text: str) -> Tuple[str, str]:
    # cuts the raw blob at the first "exclusion criteria" style header,
    # everything before it is treated as inclusion text, everything from
    # the header onward (header included) is treated as exclusion text
    match = re.search(r"exclusion\s*criteria[a-z\s]*:?", text, re.I)
    if not match:
        return text, ""  # no exclusion header found, whole text is inclusion
    return text[: match.start()], text[match.start():]


def split_bullets(section_text: str) -> List[str]:
    # breaks one section's text into individual criterion lines, trying
    # bullet markers first since most trials use them, falling back to
    # plain newlines, and finally to sentences for header-less prose sections
    if not section_text.strip():
        return []

    bullet_pattern = re.compile(r"\n\s*(?:[*\-•]|\d+[.)])\s+")
    pieces = bullet_pattern.split(section_text)
    pieces = [p.strip() for p in pieces if p.strip()]

    # the first piece is usually just the section header ("Inclusion Criteria:")
    # with no real content, so drop it once real bullets were found
    if len(pieces) > 1:
        header_like = len(pieces[0]) < 40 and ":" in pieces[0]
        return pieces[1:] if header_like else pieces

    # no bullet markers matched, split on newlines instead
    lines = [ln.strip("* -\t") for ln in section_text.split("\n")]
    lines = [ln.strip() for ln in lines if ln.strip() and ":" not in ln[-1:]]
    if len(lines) > 1:
        return lines

    # still just one blob (prose style, e.g. "DISEASE CHARACTERISTICS: ..."),
    # fall back to splitting on sentence boundaries
    sentences = re.split(r"(?<=[.;])\s+(?=[A-Z])", section_text.strip())
    return [s.strip() for s in sentences if s.strip()]


def categorize(criterion_text: str) -> str:
    # returns the first matching category label from the lexicon above,
    # or "other" when nothing recognizable was found in the line, word
    # boundaries keep short keywords like "age" from matching inside an
    # unrelated word such as "stage" or "manage"
    lowered = criterion_text.lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(re.search(rf"\b{re.escape(keyword)}", lowered) for keyword in keywords):
            return category
    return "other"


def is_negated(criterion_text: str) -> bool:
    # flags lines phrased as a negative requirement, e.g. "No history of ...",
    # a lightweight stand in for the negation cues used in clinical nlp (NegEx)
    return bool(re.match(r"^(no|not|none|excluded?|unable|without|absence of)\b", criterion_text.strip(), re.I))


def _build_items(section_text: str) -> List[CriterionItem]:
    # turns raw section text into the list of CriterionItem records the
    # rest of the project works with
    items = []
    for bullet in split_bullets(section_text):
        items.append(CriterionItem(text=bullet, category=categorize(bullet), negated=is_negated(bullet)))
    return items


def parse_trial(record: dict) -> StructuredCriteria:
    # top level entry point, takes one raw trial record (the same shape
    # produced by fetch_trials.py and stored in data/sample_trials.json)
    # and returns the fully structured result
    text = record.get("eligibility_text", "")
    title = record.get("title", "")
    inclusion_text, exclusion_text = split_sections(text)
    # the title sometimes carries the age range itself (e.g. "... 6-17 Years of Age"),
    # so it is searched together with the body rather than on its own
    combined = title + ". " + text
    minimum_age, maximum_age = extract_age_range(combined)

    return StructuredCriteria(
        nct_id=record.get("nct_id", "UNKNOWN"),
        title=title,
        conditions=record.get("conditions", []),
        sex=extract_sex(combined),
        minimum_age_years=minimum_age,
        maximum_age_years=maximum_age,
        inclusion=_build_items(inclusion_text),
        exclusion=_build_items(exclusion_text),
    )
