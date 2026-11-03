# tests.py
#
# checks that the notes are consistent, that the checker trusts faithful summaries, and that it
# catches the planted errors it is supposed to. run with: python -m unittest tests -v

import unittest

from checker import check_summary, unsupported
from notes import NOTES, gold_summary
from plant import KINDS, plant

EASY_KINDS = KINDS[:6]


class NoteTests(unittest.TestCase):
    def test_twenty_notes_with_unique_ids(self):
        self.assertEqual(len(NOTES), 20)
        self.assertEqual(len({n["id"] for n in NOTES}), 20)

    def test_every_fact_appears_in_its_note(self):
        for n in NOTES:
            text = n["text"].lower()
            for drug, dose in n["meds"]:
                self.assertIn(drug, text)
                self.assertIn(dose.split()[0], text)
            for a in n["allergies"]:
                self.assertIn(a, text)
            for _, value, _ in n["labs"]:
                self.assertIn(value, text)


class CheckerTests(unittest.TestCase):
    def test_gold_summaries_raise_nothing(self):
        for n in NOTES:
            self.assertEqual(unsupported(check_summary(n["text"], gold_summary(n))), [], n["id"])

    def test_invented_drug(self):
        n = NOTES[0]
        flagged = unsupported(check_summary(n["text"], "Takes warfarin 5 mg."))
        self.assertIn("warfarin", [c.text for c in flagged])

    def test_wrong_dose(self):
        n = NOTES[0]
        flagged = unsupported(check_summary(n["text"], "Takes metformin 1000 mg."))
        self.assertEqual([c.kind for c in flagged], ["dose"])

    def test_ruled_out_condition_is_flagged(self):
        n = NOTES[0]
        flagged = unsupported(check_summary(n["text"], "History of asthma."))
        self.assertEqual(flagged[0].reason, "the note says this was ruled out")

    def test_summary_that_denies_a_condition_is_fine(self):
        n = NOTES[0]
        self.assertEqual(unsupported(check_summary(n["text"], "No history of asthma.")), [])

    def test_general_diabetes_is_backed_by_type_2(self):
        n = NOTES[0]
        self.assertEqual(unsupported(check_summary(n["text"], "Patient has diabetes.")), [])

    def test_wrong_age(self):
        n = NOTES[0]
        flagged = unsupported(check_summary(n["text"], "A 41 year old man."))
        self.assertEqual(flagged[0].kind, "number")


class PlantedTests(unittest.TestCase):
    def test_easy_planted_errors_are_caught(self):
        for n in NOTES:
            for kind in EASY_KINDS:
                planted = plant(n, kind)
                if planted is None:
                    continue
                summary, key = planted
                flagged = unsupported(check_summary(n["text"], summary))
                self.assertTrue(any(key.lower() in c.text.lower() for c in flagged), (n["id"], kind))

    def test_planting_is_repeatable(self):
        self.assertEqual(plant(NOTES[0], "fake_drug", 3), plant(NOTES[0], "fake_drug", 3))


if __name__ == "__main__":
    unittest.main()
