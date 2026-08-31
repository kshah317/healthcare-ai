from dataclasses import dataclass, field
from typing import List, Optional

# the shapes below are the shared vocabulary between the parser, the cli,
# and the tests, everything downstream reads and writes these two shapes
# so a trial always ends up structured the same way no matter where it came from


@dataclass
class CriterionItem:
    # one bullet or sentence pulled out of a trial's eligibility text
    text: str  # the original wording, kept as is so nothing gets lost
    category: str  # a short label like "age", "pregnancy", "prior_therapy"
    negated: bool  # true if the line reads like a "no ..." / "not ..." exclusion


@dataclass
class StructuredCriteria:
    # the full structured result for a single trial
    nct_id: str  # the clinicaltrials.gov identifier, e.g. NCT01234567
    title: str  # human readable trial title
    conditions: List[str]  # the conditions the trial is studying
    sex: str  # "FEMALE", "MALE", or "ALL", parsed from the free text
    minimum_age_years: Optional[float]  # lowest qualifying age in years, if found
    maximum_age_years: Optional[float]  # highest qualifying age in years, if found
    inclusion: List[CriterionItem] = field(default_factory=list)  # who qualifies
    exclusion: List[CriterionItem] = field(default_factory=list)  # who is ruled out

    def summary(self) -> str:
        # a short one line description, handy for printing in the cli
        age_bits = []
        if self.minimum_age_years is not None:
            age_bits.append(f">= {self.minimum_age_years:g}y")
        if self.maximum_age_years is not None:
            age_bits.append(f"<= {self.maximum_age_years:g}y")
        age_text = " and ".join(age_bits) if age_bits else "no age limit found"
        return (
            f"{self.nct_id}: {self.title} | sex={self.sex} | {age_text} | "
            f"{len(self.inclusion)} inclusion items, {len(self.exclusion)} exclusion items"
        )
