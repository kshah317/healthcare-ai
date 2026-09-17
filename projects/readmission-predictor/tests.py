"""
unit tests for the cleaning and modeling logic. these use small, hand-built fixtures
instead of the real 18mb dataset, so the whole test suite runs in under a second and
never needs an internet connection. one end-to-end test at the bottom does use the real
dataset, but only if it's already been downloaded, and skips itself cleanly otherwise.
"""

# unittest is python's built-in testing framework
import unittest
# os.path is used to check whether the real dataset has been downloaded yet
import os.path
# pandas is used to build the small synthetic dataframes each test needs
import pandas as pd
# numpy is used for a couple of numeric comparisons
import numpy as np

# everything we're testing lives in preprocess.py
from preprocess import (
    bucket_icd9_code,
    remove_leakage_rows,
    binarize_target,
    clean_dataset,
    split_features_target_and_groups,
    patient_level_train_test_split,
    load_raw_data,
)
# and the model-building/evaluation functions from model.py
from model import build_logistic_regression_pipeline, train_pipeline, evaluate_pipeline


class Icd9BucketingTests(unittest.TestCase):
    """checks that raw ICD-9 codes get sorted into the right clinical category"""

    def test_diabetes_code_maps_to_diabetes(self):
        # 250.83 is a real diabetes code from the dataset itself
        self.assertEqual(bucket_icd9_code("250.83"), "diabetes")

    def test_circulatory_code_maps_to_circulatory(self):
        # 410 is acute myocardial infarction, squarely in the circulatory range
        self.assertEqual(bucket_icd9_code("410"), "circulatory")

    def test_respiratory_code_maps_to_respiratory(self):
        # 486 is pneumonia, in the respiratory range
        self.assertEqual(bucket_icd9_code("486"), "respiratory")

    def test_v_code_maps_to_other(self):
        # V-codes are supplemental classification codes, not a specific disease
        self.assertEqual(bucket_icd9_code("V27"), "other")

    def test_e_code_maps_to_other(self):
        # E-codes describe external causes of injury, also not a specific disease
        self.assertEqual(bucket_icd9_code("E888"), "other")

    def test_missing_code_maps_to_missing(self):
        # a genuinely missing diagnosis should get its own category, not crash or vanish
        self.assertEqual(bucket_icd9_code(np.nan), "missing")

    def test_unrecognized_text_falls_back_to_other(self):
        # anything unparseable should fail safe into "other" rather than raising an error
        self.assertEqual(bucket_icd9_code("not-a-code"), "other")


class LeakageRemovalTests(unittest.TestCase):
    """checks that expired/hospice encounters are correctly filtered out"""

    def test_expired_row_is_removed(self):
        # build a tiny two-row dataframe: one normal discharge, one "expired" discharge
        tiny_df = pd.DataFrame({
            "discharge_disposition_id": [1, 11],  # 1 = discharged to home, 11 = expired
            "patient_nbr": [111, 222],
        })
        cleaned = remove_leakage_rows(tiny_df)
        # only the row with discharge_disposition_id == 1 should survive
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned.iloc[0]["discharge_disposition_id"], 1)

    def test_all_hospice_codes_are_removed(self):
        # every code in this list should be filtered out
        hospice_codes = [13, 14, 19, 20, 21]
        tiny_df = pd.DataFrame({
            "discharge_disposition_id": hospice_codes,
            "patient_nbr": range(len(hospice_codes)),
        })
        cleaned = remove_leakage_rows(tiny_df)
        # none of the hospice rows should survive, so the result should be empty
        self.assertEqual(len(cleaned), 0)


class TargetBinarizationTests(unittest.TestCase):
    """checks that the three-way readmitted column becomes the right 0/1 values"""

    def test_less_than_30_becomes_one(self):
        tiny_df = pd.DataFrame({"readmitted": ["<30"]})
        result = binarize_target(tiny_df)
        self.assertEqual(result.iloc[0]["readmitted_within_30_days"], 1)

    def test_greater_than_30_becomes_zero(self):
        tiny_df = pd.DataFrame({"readmitted": [">30"]})
        result = binarize_target(tiny_df)
        self.assertEqual(result.iloc[0]["readmitted_within_30_days"], 0)

    def test_no_becomes_zero(self):
        tiny_df = pd.DataFrame({"readmitted": ["NO"]})
        result = binarize_target(tiny_df)
        self.assertEqual(result.iloc[0]["readmitted_within_30_days"], 0)

    def test_original_column_is_dropped(self):
        # the three-way column should not survive, to avoid it accidentally leaking into the model
        tiny_df = pd.DataFrame({"readmitted": ["<30"]})
        result = binarize_target(tiny_df)
        self.assertNotIn("readmitted", result.columns)


class PatientLevelSplitTests(unittest.TestCase):
    """checks that the same patient never ends up in both the train and test sets"""

    def test_no_patient_overlap_between_train_and_test(self):
        # build 40 rows belonging to only 10 distinct patients, several rows each,
        # so a naive random split would almost certainly split some patients across both sides
        patient_ids = list(range(10)) * 4  # each of the 10 patient ids appears 4 times
        X = pd.DataFrame({
            "feature_a": range(len(patient_ids)),
        })
        y = pd.Series([0, 1] * (len(patient_ids) // 2))
        groups = pd.Series(patient_ids)
        audit_attributes = pd.DataFrame({
            "race": ["Caucasian"] * len(patient_ids),
            "gender": ["Female"] * len(patient_ids),
        })

        X_train, X_test, y_train, y_test, audit_test = patient_level_train_test_split(
            X, y, groups, audit_attributes, test_size=0.3, random_state=1
        )

        # recover which original row indices ended up in train vs test
        train_patient_ids = set(groups.iloc[X_train.index])
        test_patient_ids = set(groups.iloc[X_test.index])

        # the intersection of the two sets of patient ids must be empty
        self.assertEqual(train_patient_ids & test_patient_ids, set())


class EndToEndPipelineTests(unittest.TestCase):
    """
    a slower, more realistic test that runs the full pipeline on the real dataset.
    this only runs if data/diabetic_data.csv already exists on disk, since we don't
    want the everyday test run to require an 18mb download
    """

    def test_full_pipeline_produces_valid_probabilities(self):
        # skip this test entirely if the real data hasn't been downloaded yet
        if not os.path.exists("data/diabetic_data.csv"):
            self.skipTest("data/diabetic_data.csv not found, run fetch_data.py first to enable this test")

        # run the exact same steps cli.py runs, just on a smaller slice for speed
        raw_df = load_raw_data("data/diabetic_data.csv")
        # take a random sample of 5000 rows so this test finishes in a couple of seconds
        raw_df = raw_df.sample(n=5000, random_state=1)
        clean_df = clean_dataset(raw_df)
        X, y, groups, audit_attributes = split_features_target_and_groups(clean_df)
        X_train, X_test, y_train, y_test, audit_test = patient_level_train_test_split(
            X, y, groups, audit_attributes
        )

        # train just the fast logistic regression model for this smoke test
        pipeline = train_pipeline(build_logistic_regression_pipeline(), X_train, y_train)
        results = evaluate_pipeline(pipeline, X_test, y_test)

        # every predicted probability must be a valid probability between 0 and 1
        probabilities = results["predicted_probabilities"]
        self.assertTrue((probabilities >= 0).all() and (probabilities <= 1).all())
        # roc_auc should be a real number, not NaN, and better than pure random guessing
        self.assertFalse(np.isnan(results["roc_auc"]))
        self.assertGreater(results["roc_auc"], 0.5)


# lets this file be run directly with "python tests.py" in addition to "python -m unittest"
if __name__ == "__main__":
    unittest.main()
