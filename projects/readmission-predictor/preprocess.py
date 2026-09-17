"""
this file turns the raw hospital csv into something a model can actually learn from.
raw electronic health record exports are messy: missing values written as "?", diagnosis
codes that are just numbers with no clinical meaning to a model, and a handful of rows
that would leak the answer if left in. everything in this file exists to fix one of
those problems, and every function is small on purpose so each cleaning decision is easy
to point to and explain on its own.
"""

# pandas gives us the dataframe structure we use to hold and transform the tabular data
import pandas as pd
# numpy is used for the small numeric helpers, like building boolean masks
import numpy as np
# GroupShuffleSplit splits data by a group id (patient) instead of by row, so the same
# patient's encounters never end up split across both the train and test sets
from sklearn.model_selection import GroupShuffleSplit

# these are the discharge_disposition_id codes that mean the patient died or entered
# hospice care during this encounter, taken directly from the dataset's own IDs_mapping.csv
# file, not guessed. a patient who died cannot be readmitted, so leaving these rows in
# would let the model "learn" from outcomes that were never actually possible, which is a
# textbook case of data leakage
EXPIRED_OR_HOSPICE_DISPOSITION_IDS = {11, 13, 14, 19, 20, 21}  # 11=expired, 13/14=hospice, 19-21=expired+hospice combos

# columns that are almost entirely missing, purely administrative, or too sparse to trust,
# so we drop them outright rather than trying to impute values we don't actually have
COLUMNS_TO_DROP = [
    "weight",           # missing in about 97% of rows, not usable
    "payer_code",       # billing detail, not a clinical signal, and heavily missing
    "medical_specialty",  # missing in roughly half the rows, dropped to keep this simple
]

# the 20+ individual diabetes medication columns (metformin, glipizide, and so on) are
# almost all "No" for almost every patient, so one-hot encoding all of them would add a
# lot of near-useless columns. we keep only the handful of medication-related fields that
# actually carry a useful signal about how aggressively a patient's diabetes was managed
MEDICATION_COLUMNS_TO_KEEP = ["insulin", "change", "diabetesMed", "max_glu_serum", "A1Cresult"]

# every other individual drug column gets dropped, this list is just "all 23 columns minus
# the ones we kept above", written out explicitly so nothing is dropped by accident
ALL_MEDICATION_COLUMNS = [
    "metformin", "repaglinide", "nateglinide", "chlorpropamide", "glimepiride",
    "acetohexamide", "glipizide", "glyburide", "tolbutamide", "pioglitazone",
    "rosiglitazone", "acarbose", "miglitol", "troglitazone", "tolazamide",
    "examide", "citoglipton", "insulin", "glyburide-metformin", "glipizide-metformin",
    "glimepiride-pioglitazone", "metformin-rosiglitazone", "metformin-pioglitazone",
]
# this builds the actual drop list: every medication column that is not in our keep list
MEDICATION_COLUMNS_TO_DROP = [c for c in ALL_MEDICATION_COLUMNS if c not in MEDICATION_COLUMNS_TO_KEEP]

# these are the numeric columns we hand to the model as-is, since they're already clean
# integer counts with no missing values in this dataset
NUMERIC_FEATURE_COLUMNS = [
    "time_in_hospital",     # how many days the patient stayed, longer stays often mean sicker patients
    "num_lab_procedures",   # how many lab tests were run during the stay
    "num_procedures",       # how many non-lab procedures were performed
    "num_medications",      # how many distinct medications were given during the stay
    "number_outpatient",    # outpatient visits in the year before this admission
    "number_emergency",     # emergency room visits in the year before this admission
    "number_inpatient",     # inpatient admissions in the year before this admission, often the strongest signal
    "number_diagnoses",     # how many total diagnoses were recorded for this encounter
]

# these are the categorical columns we hand to the model. age is included here because
# age is a legitimate, clinically standard risk factor. race and gender are deliberately
# left out of this list, see the docstring further down for why
CATEGORICAL_FEATURE_COLUMNS = [
    "age",                     # ten-year age bands, e.g. "[70-80)"
    "admission_type_id",       # emergency, urgent, elective, and so on
    "discharge_disposition_id",  # where the patient went after this stay
    "admission_source_id",     # how the patient arrived, e.g. referral vs emergency room
    "diag_1_category",         # engineered below: primary diagnosis, bucketed into a clinical category
    "diag_2_category",         # engineered below: secondary diagnosis category
    "diag_3_category",         # engineered below: tertiary diagnosis category
] + MEDICATION_COLUMNS_TO_KEEP  # add the medication-management columns we decided to keep

# race and gender are read from the raw data purely so the fairness audit can slice
# predictions by them later. they are never passed into the model as inputs
AUDIT_ONLY_COLUMNS = ["race", "gender"]

# this is the column that uniquely identifies a patient across multiple hospital visits,
# used only to make sure one patient's rows never end up in both train and test
PATIENT_ID_COLUMN = "patient_nbr"


def load_raw_data(csv_path):
    """
    reads the raw diabetic_data.csv file into a dataframe.
    the dataset uses the literal string "?" for missing values instead of a blank cell,
    so we tell pandas to treat "?" as NaN right away, otherwise it would be treated as
    a normal text category and quietly corrupt every downstream step
    """
    # na_values=["?"] converts every "?" cell straight into a proper missing value.
    # low_memory=False reads the whole file in one pass so pandas doesn't guess a
    # column's type from just the first chunk and then warn about it being mixed later
    raw_df = pd.read_csv(csv_path, na_values=["?"], low_memory=False)
    # hand back the loaded dataframe to whoever called this function
    return raw_df


def bucket_icd9_code(raw_code):
    """
    converts a single raw ICD-9 diagnosis code into one of nine broad clinical categories.
    ICD-9 codes are just numbers (with a few letter-prefixed exceptions) and mean nothing
    to a model on their own, there are hundreds of distinct codes in this dataset, so
    treating each one as its own category would make the model impossibly sparse.
    grouping them into clinically meaningful buckets is the standard approach used in the
    original study this dataset comes from.
    """
    # a missing diagnosis code gets its own explicit category rather than being dropped
    if pd.isna(raw_code):
        return "missing"  # keeps the row instead of throwing away otherwise-good data

    # codes that start with "V" or "E" are supplemental classification codes (things like
    # "follow-up exam" or "external cause of injury"), not a specific disease, so they
    # all fall into the catch-all "other" bucket
    code_text = str(raw_code)  # make sure we're working with a string, not a float
    if code_text.startswith("V") or code_text.startswith("E"):
        return "other"  # supplemental codes don't map to one of the numeric disease ranges below

    # every remaining code should be a plain number, sometimes with a decimal like "250.83"
    try:
        # only the part before the decimal point matters for bucketing into a category
        numeric_code = float(code_text)
    except ValueError:
        # if for any reason the code isn't a valid number, fall back to "other" instead of crashing
        return "other"

    # diabetes codes all start with 250, and diabetes gets its own bucket since this whole
    # dataset is specifically about diabetic patients
    if 250 <= numeric_code < 251:
        return "diabetes"
    # circulatory system diseases, e.g. heart disease, hypertension
    if 390 <= numeric_code <= 459 or numeric_code == 785:
        return "circulatory"
    # respiratory system diseases, e.g. pneumonia, asthma
    if 460 <= numeric_code <= 519 or numeric_code == 786:
        return "respiratory"
    # digestive system diseases, e.g. ulcers, liver disease
    if 520 <= numeric_code <= 579 or numeric_code == 787:
        return "digestive"
    # injury and poisoning codes
    if 800 <= numeric_code <= 999:
        return "injury"
    # musculoskeletal system diseases, e.g. arthritis
    if 710 <= numeric_code <= 739:
        return "musculoskeletal"
    # genitourinary system diseases, e.g. kidney disease
    if 580 <= numeric_code <= 629 or numeric_code == 788:
        return "genitourinary"
    # neoplasms, meaning tumors, benign or malignant
    if 140 <= numeric_code <= 239:
        return "neoplasms"
    # anything left over that doesn't fall into one of the buckets above
    return "other"


def add_diagnosis_categories(df):
    """
    applies bucket_icd9_code to each of the three diagnosis columns and stores the result
    in new columns, so the model sees a small set of clinical categories instead of
    hundreds of raw numeric codes
    """
    # .apply runs bucket_icd9_code once for every value in the diag_1 column
    df["diag_1_category"] = df["diag_1"].apply(bucket_icd9_code)
    # same bucketing logic applied to the secondary diagnosis
    df["diag_2_category"] = df["diag_2"].apply(bucket_icd9_code)
    # same bucketing logic applied to the tertiary diagnosis
    df["diag_3_category"] = df["diag_3"].apply(bucket_icd9_code)
    # return the dataframe with the three new columns attached
    return df


def remove_leakage_rows(df):
    """
    drops every encounter where the patient died or was discharged to hospice.
    a patient who died during this hospital stay cannot, by definition, come back within
    30 days, so keeping these rows would hand the model a set of guaranteed-negative
    outcomes that have nothing to do with the quality of their care
    """
    # build a true/false mask: True means "this row's discharge code is one of the
    # expired-or-hospice codes and should be removed"
    is_leakage_row = df["discharge_disposition_id"].isin(EXPIRED_OR_HOSPICE_DISPOSITION_IDS)
    # keep only the rows where the mask is False, i.e. everything that isn't a leakage row
    cleaned_df = df[~is_leakage_row].copy()  # .copy() avoids a pandas "view vs copy" warning later
    # hand back the filtered dataframe
    return cleaned_df


def binarize_target(df):
    """
    turns the three-way "readmitted" column ("NO", ">30", "<30") into a single 0/1 column.
    the hospital penalty this project is modeling only cares about readmission within 30
    days, so ">30" and "NO" both count as a negative outcome, and "<30" is the only
    positive outcome
    """
    # a row is a positive case only if the original value is exactly "<30"
    df["readmitted_within_30_days"] = (df["readmitted"] == "<30").astype(int)  # True/False becomes 1/0
    # the original three-way column is no longer needed once we have the binary version
    df = df.drop(columns=["readmitted"])
    # hand back the dataframe with the new binary target column
    return df


def clean_dataset(raw_df):
    """
    runs the full cleaning pipeline in order: drop unusable columns, engineer the
    diagnosis categories, remove leakage rows, and binarize the target. this is the one
    function the rest of the project calls, so all the cleaning steps happen in a single,
    predictable order every time
    """
    # start from a copy so we never accidentally mutate the caller's original dataframe
    df = raw_df.copy()
    # remove the columns we decided are too sparse or not clinically useful
    df = df.drop(columns=COLUMNS_TO_DROP)
    # remove the individual medication columns we decided not to keep
    df = df.drop(columns=MEDICATION_COLUMNS_TO_DROP)
    # add the diag_1_category / diag_2_category / diag_3_category columns
    df = add_diagnosis_categories(df)
    # drop rows where the patient died or entered hospice, see remove_leakage_rows above
    df = remove_leakage_rows(df)
    # convert the three-way readmitted column into a single 0/1 target column
    df = binarize_target(df)
    # hand back the fully cleaned dataframe
    return df


def split_features_target_and_groups(clean_df):
    """
    splits the cleaned dataframe into three pieces: the feature columns the model trains
    on (X), the target column it predicts (y), and the patient id for each row (groups),
    which is needed to do a patient-level train/test split instead of a naive random one
    """
    # X is every column the model is actually allowed to see
    feature_columns = NUMERIC_FEATURE_COLUMNS + CATEGORICAL_FEATURE_COLUMNS
    X = clean_df[feature_columns].copy()
    # y is the binary target we're trying to predict
    y = clean_df["readmitted_within_30_days"].copy()
    # groups is the patient id, used only for splitting, never as a model input
    groups = clean_df[PATIENT_ID_COLUMN].copy()
    # audit_attributes carries race and gender alongside the test set for the fairness
    # check, kept separate from X so they never accidentally leak into training.
    # missing race values are filled with the explicit label "Unknown" instead of being
    # left as NaN, since a NaN can never equal another NaN, which would otherwise make
    # those rows silently disappear from every subgroup count in the fairness audit
    audit_attributes = clean_df[AUDIT_ONLY_COLUMNS].copy()
    audit_attributes["race"] = audit_attributes["race"].fillna("Unknown")
    # hand back all four pieces together
    return X, y, groups, audit_attributes


def patient_level_train_test_split(X, y, groups, audit_attributes, test_size=0.2, random_state=42):
    """
    splits the data into train and test sets by patient rather than by row. if the same
    patient appears in both the training set and the test set, the model could partly
    "recognize" that patient instead of genuinely generalizing to new people, which would
    make the test accuracy look better than it would be in the real world
    """
    # GroupShuffleSplit with n_splits=1 gives us exactly one train/test partition
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    # .split returns the row positions for train and test as two arrays of indices
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))
    # .iloc selects rows by position, which is what train_idx/test_idx contain
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    # only the test half of the audit attributes is needed, since fairness is checked
    # against held-out predictions, not against training data
    audit_test = audit_attributes.iloc[test_idx]
    # hand back everything the caller needs to train and then evaluate the model
    return X_train, X_test, y_train, y_test, audit_test
