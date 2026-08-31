import json
import os
import unittest

import criteria_parser as parser

# standard library unittest only, no external test framework, keeps the
# project dependency free, run with: python -m unittest tests.py

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "sample_trials.json")


class AgeExtractionTests(unittest.TestCase):
    # each case below is phrased the way a real trial phrases it, pulled
    # from patterns actually seen in data/sample_trials.json

    def test_simple_range_with_unit(self):
        lo, hi = parser.extract_age_range("Ages 18-65 years")
        self.assertEqual((lo, hi), (18.0, 65.0))

    def test_dual_bound_symbols(self):
        lo, hi = parser.extract_age_range("Age >= 18 <= 60 years")
        self.assertEqual((lo, hi), (18.0, 60.0))

    def test_trailing_years_of_age_phrasing(self):
        lo, hi = parser.extract_age_range("child 8-12 years of age with a diagnosis")
        self.assertEqual((lo, hi), (8.0, 12.0))

    def test_and_over_phrasing(self):
        lo, hi = parser.extract_age_range("Age: 18 and over")
        self.assertEqual((lo, hi), (18.0, None))

    def test_aged_to_phrasing(self):
        lo, hi = parser.extract_age_range("Aged 21 to 75 both inclusive")
        self.assertEqual((lo, hi), (21.0, 75.0))

    def test_no_age_mentioned_returns_none(self):
        lo, hi = parser.extract_age_range("must sign the informed consent form")
        self.assertEqual((lo, hi), (None, None))

    def test_unrelated_numbers_are_not_mistaken_for_age(self):
        # this is the case that broke the first version of the regex,
        # "BMI > 45" should never be read as an age
        lo, hi = parser.extract_age_range("Exclusion Criteria: BMI > 45 kg/m2")
        self.assertEqual((lo, hi), (None, None))

    def test_months_are_converted_to_years(self):
        lo, hi = parser.extract_age_range("age 18 months and over")
        self.assertAlmostEqual(lo, 1.5)


class SexExtractionTests(unittest.TestCase):

    def test_explicit_female(self):
        self.assertEqual(parser.extract_sex("Sex: Female"), "FEMALE")

    def test_explicit_male(self):
        self.assertEqual(parser.extract_sex("Male subjects only"), "MALE")

    def test_both_mentioned_is_all(self):
        self.assertEqual(parser.extract_sex("Male or female subjects"), "ALL")

    def test_unspecified_defaults_to_all(self):
        self.assertEqual(parser.extract_sex("must be able to give consent"), "ALL")

    def test_postmenopausal_women_counts_as_female(self):
        self.assertEqual(parser.extract_sex("postmenopausal women only"), "FEMALE")

    def test_pregnancy_exclusion_does_not_imply_female_only(self):
        # "pregnant women" shows up as a routine exclusion in mixed sex trials,
        # it must not be read as a signal that the trial is female only
        text = "Exclusion Criteria: pregnant or nursing women, chronic illness"
        self.assertEqual(parser.extract_sex(text), "ALL")


class SectionSplittingTests(unittest.TestCase):

    def test_splits_on_exclusion_header(self):
        text = "Inclusion Criteria:\n* over 18\n\nExclusion Criteria:\n* pregnant"
        inclusion, exclusion = parser.split_sections(text)
        self.assertIn("over 18", inclusion)
        self.assertIn("pregnant", exclusion)
        self.assertNotIn("pregnant", inclusion)

    def test_no_exclusion_header_puts_everything_in_inclusion(self):
        text = "Inclusion Criteria:\n* over 18\n* able to consent"
        inclusion, exclusion = parser.split_sections(text)
        self.assertEqual(exclusion, "")
        self.assertIn("able to consent", inclusion)


class BulletSplittingTests(unittest.TestCase):

    def test_splits_on_asterisk_bullets(self):
        bullets = parser.split_bullets("Inclusion Criteria:\n* first item\n* second item")
        self.assertEqual(bullets, ["first item", "second item"])

    def test_splits_on_numbered_bullets(self):
        bullets = parser.split_bullets("Inclusion Criteria:\n1. first item\n2. second item")
        self.assertEqual(bullets, ["first item", "second item"])

    def test_empty_section_returns_empty_list(self):
        self.assertEqual(parser.split_bullets(""), [])


class CategorizationTests(unittest.TestCase):

    def test_pregnancy_keyword(self):
        self.assertEqual(parser.categorize("currently pregnant or breastfeeding"), "pregnancy")

    def test_lab_value_keyword(self):
        self.assertEqual(parser.categorize("creatinine clearance < 30 mL/min"), "lab_values")

    def test_unmatched_falls_back_to_other(self):
        self.assertEqual(parser.categorize("owns a working smartphone with a camera"), "logistics")


class NegationTests(unittest.TestCase):

    def test_leading_no_is_negated(self):
        self.assertTrue(parser.is_negated("No history of seizures"))

    def test_plain_statement_is_not_negated(self):
        self.assertFalse(parser.is_negated("Age 18 years or older"))


class EndToEndTests(unittest.TestCase):
    # loads the real bundled sample data and checks that the whole pipeline
    # holds up to a reasonable accuracy bar against ground truth fields
    # that clinicaltrials.gov already stores separately from the free text

    @classmethod
    def setUpClass(cls):
        with open(DATA_PATH, "r", encoding="utf-8") as handle:
            cls.trials = json.load(handle)

    def test_sample_data_loads(self):
        self.assertGreater(len(self.trials), 10)

    def test_every_trial_parses_without_error(self):
        for trial in self.trials:
            structured = parser.parse_trial(trial)
            self.assertEqual(structured.nct_id, trial["nct_id"])

    def test_sex_accuracy_meets_bar(self):
        correct = sum(
            parser.parse_trial(t).sex == t["known_sex"] for t in self.trials
        )
        accuracy = correct / len(self.trials)
        self.assertGreaterEqual(accuracy, 0.9, f"sex accuracy too low: {accuracy:.0%}")

    def test_minimum_age_accuracy_meets_bar(self):
        checked = [t for t in self.trials if t.get("known_minimum_age")]
        correct = 0
        for trial in checked:
            structured = parser.parse_trial(trial)
            known = float(trial["known_minimum_age"].split()[0])
            correct += structured.minimum_age_years == known
        accuracy = correct / len(checked)
        self.assertGreaterEqual(accuracy, 0.75, f"minimum age accuracy too low: {accuracy:.0%}")


if __name__ == "__main__":
    unittest.main()
