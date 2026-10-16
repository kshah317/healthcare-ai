# test_explore_patients.py
#
# tests for explore_patients.py. each test writes a tiny made-up set of synthea-style csv files
# into a temporary folder, so nothing here needs java, the synthea download, or real data.

import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

import explore_patients as explore

# a fixed "today" keeps the age math the same no matter when the tests run
TODAY = date(2026, 6, 15)


def make_tables():
    # four people: two women, two men, and one of the men has died
    patients = pd.DataFrame(
        {
            "Id": ["p1", "p2", "p3", "p4"],
            "BIRTHDATE": ["2000-06-15", "1990-12-01", "1950-01-01", "1980-03-10"],
            "DEATHDATE": [None, None, None, "2020-05-05"],
            "GENDER": ["F", "F", "M", "M"],
        }
    )
    conditions = pd.DataFrame(
        {
            "PATIENT": ["p1", "p2", "p2", "p3", "p3"],
            "DESCRIPTION": ["Asthma", "Asthma", "Asthma", "Diabetes", "Asthma"],
        }
    )
    medications = pd.DataFrame(
        {"PATIENT": ["p1", "p3"], "DESCRIPTION": ["Inhaler", "Insulin"]}
    )
    encounters = pd.DataFrame({"PATIENT": ["p1", "p1", "p1", "p2", "p3"]})
    return {
        "patients": patients,
        "conditions": conditions,
        "medications": medications,
        "encounters": encounters,
    }


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.summary = explore.summarize(make_tables(), today=TODAY)

    def test_counts_patients_and_living(self):
        self.assertEqual(self.summary["patients"], 4)
        self.assertEqual(self.summary["living"], 3)

    def test_gender_split(self):
        self.assertEqual(self.summary["gender"], {"F": 2, "M": 2})

    def test_ages_only_count_living_patients(self):
        # p1 just turned 26 today, p2 is 35, p3 is 76, the deceased p4 is left out
        self.assertEqual(self.summary["age_min"], 26)
        self.assertEqual(self.summary["age_median"], 35.0)
        self.assertEqual(self.summary["age_max"], 76)

    def test_birthday_not_yet_reached_takes_a_year_off(self):
        patients = pd.DataFrame(
            {"BIRTHDATE": ["2000-06-16"], "DEATHDATE": [None]}
        )
        ages = explore.ages_of_living_patients(patients, TODAY)
        self.assertEqual(int(ages.iloc[0]), 25)

    def test_top_conditions_count_each_patient_once(self):
        # p2 has asthma twice but still only counts as one patient
        self.assertEqual(self.summary["top_conditions"]["Asthma"], 3)
        self.assertEqual(self.summary["top_conditions"]["Diabetes"], 1)

    def test_visits_include_people_with_none(self):
        # p1 had 3 visits, p2 and p3 had 1 each, p4 had none
        self.assertEqual(self.summary["visits_max"], 3)
        self.assertEqual(self.summary["visits_median"], 1.0)


class LoadTests(unittest.TestCase):
    def test_missing_folder_gives_helpful_error(self):
        with self.assertRaises(FileNotFoundError) as caught:
            explore.load_tables(Path("definitely-not-a-real-folder"))
        self.assertIn("generate_patients.py", str(caught.exception))

    def test_missing_table_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                explore.load_tables(folder)

    def test_loads_all_four_tables(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, table in make_tables().items():
                table.to_csv(Path(folder) / f"{name}.csv", index=False)
            loaded = explore.load_tables(folder)
        self.assertEqual(sorted(loaded), sorted(explore.TABLE_NAMES))
        self.assertEqual(len(loaded["patients"]), 4)


if __name__ == "__main__":
    unittest.main()
