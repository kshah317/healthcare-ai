"""
a menu driven demo that ties the whole project together: load the data, clean it, train
both models, compare them, run the fairness audit, and score a made-up patient. this is
the file to run if you just want to see the project work without reading the other files
first.
"""

# os.path is used to check whether the raw data has already been downloaded
import os.path

# these come from preprocess.py: loading and cleaning the raw csv, and splitting it into
# a proper patient-level train/test set
from preprocess import (
    load_raw_data,
    clean_dataset,
    split_features_target_and_groups,
    patient_level_train_test_split,
    NUMERIC_FEATURE_COLUMNS,
    CATEGORICAL_FEATURE_COLUMNS,
)
# these come from model.py: building, training, and scoring the two pipelines
from model import (
    build_logistic_regression_pipeline,
    build_gradient_boosting_pipeline,
    train_pipeline,
    evaluate_pipeline,
)
# this comes from fairness_audit.py: the subgroup breakdown by race and gender
from fairness_audit import run_full_fairness_audit
# this is the download helper, used only if the raw data isn't on disk yet
from fetch_data import fetch_and_prepare_dataset

# pandas is needed here to build the single-row dataframe for the "score a patient" option
import pandas as pd

# path to the raw csv file, checked at startup to decide whether we need to download it
RAW_DATA_PATH = "data/diabetic_data.csv"

# a simple dictionary used to hold everything trained during this run, so the different
# menu options can share the same trained models instead of retraining every time
session_state = {
    "logistic_pipeline": None,   # will hold the trained logistic regression pipeline
    "boosting_pipeline": None,   # will hold the trained gradient boosting pipeline
    "X_test": None,              # held-out feature rows, used by every evaluation option
    "y_test": None,              # held-out true labels, used by every evaluation option
    "audit_test": None,          # held-out race/gender columns, used only by the fairness audit
    "logistic_results": None,    # cached metrics dictionary from evaluate_pipeline
    "boosting_results": None,    # cached metrics dictionary from evaluate_pipeline
}


def ensure_data_available():
    """
    checks whether the raw csv has already been downloaded, and if not, downloads it now.
    this means a first-time user can just run cli.py without a separate setup step
    """
    # os.path.exists returns True only if the file is actually sitting on disk already
    if not os.path.exists(RAW_DATA_PATH):
        # tell the user why there's about to be a pause, downloading 18mb isn't instant
        print("raw data not found locally, downloading it now (this only happens once)...")
        # this actually performs the download and extraction, defined in fetch_data.py
        fetch_and_prepare_dataset()


def train_and_compare_models():
    """
    menu option 1: loads and cleans the data, splits it, trains both pipelines, evaluates
    them both on the same held-out test set, and prints a side-by-side comparison
    """
    # make sure we actually have the csv before trying to read it
    ensure_data_available()
    # load the raw csv into a dataframe
    raw_df = load_raw_data(RAW_DATA_PATH)
    # run the full cleaning pipeline: drop unusable columns, bucket diagnoses, remove
    # leakage rows, binarize the target
    clean_df = clean_dataset(raw_df)
    # split into features (X), target (y), patient ids (groups), and audit columns
    X, y, groups, audit_attributes = split_features_target_and_groups(clean_df)
    # split by patient so no single patient appears in both train and test
    X_train, X_test, y_train, y_test, audit_test = patient_level_train_test_split(
        X, y, groups, audit_attributes
    )

    # let the user see roughly how big the cleaned dataset is
    print(f"\ncleaned dataset: {len(clean_df):,} encounters after removing expired/hospice rows")
    print(f"training on {len(X_train):,} rows, testing on {len(X_test):,} rows\n")

    # build and train the interpretable baseline model
    print("training logistic regression...")
    logistic_pipeline = train_pipeline(build_logistic_regression_pipeline(), X_train, y_train)
    # build and train the stronger comparison model
    print("training gradient boosted trees...")
    boosting_pipeline = train_pipeline(build_gradient_boosting_pipeline(), X_train, y_train)

    # score both trained pipelines against the exact same held-out test set
    logistic_results = evaluate_pipeline(logistic_pipeline, X_test, y_test)
    boosting_results = evaluate_pipeline(boosting_pipeline, X_test, y_test)

    # save everything into session_state so later menu options don't need to retrain
    session_state["logistic_pipeline"] = logistic_pipeline
    session_state["boosting_pipeline"] = boosting_pipeline
    session_state["X_test"] = X_test
    session_state["y_test"] = y_test
    session_state["audit_test"] = audit_test
    session_state["logistic_results"] = logistic_results
    session_state["boosting_results"] = boosting_results

    # print a simple side-by-side comparison of the two headline metrics
    print("\nmodel comparison on the held-out test set:")
    print(f"{'metric':<12}{'logistic regression':<22}{'gradient boosting':<20}")
    print(f"{'roc-auc':<12}{logistic_results['roc_auc']:<22.3f}{boosting_results['roc_auc']:<20.3f}")
    print(f"{'pr-auc':<12}{logistic_results['pr_auc']:<22.3f}{boosting_results['pr_auc']:<20.3f}")
    print("\n(roc-auc: how well the model ranks true positives above true negatives)")
    print("(pr-auc: precision/recall tradeoff, more informative since positives are rare)")


def show_detailed_report():
    """
    menu option 2: prints the full confusion matrix and classification report for both
    models, only works after option 1 has been run at least once
    """
    # guard against running this before training has happened
    if session_state["logistic_results"] is None:
        print("\nrun option 1 first, there's nothing trained yet.")
        return

    # walk through both models and print their detailed results one after another
    for model_name, results_key in [("logistic regression", "logistic_results"), ("gradient boosting", "boosting_results")]:
        results = session_state[results_key]  # pull the cached metrics dictionary for this model
        print(f"\n--- {model_name} ---")
        print("confusion matrix (rows = actual, columns = predicted):")
        print(results["confusion_matrix"])  # a 2x2 grid of true/false positive/negative counts
        print(results["classification_report"])  # precision, recall, f1 in text form


def run_fairness_audit_option():
    """
    menu option 3: runs the subgroup fairness audit against the gradient boosting model's
    predictions, since that's the stronger model and the one more likely to actually be
    deployed
    """
    # guard against running this before training has happened
    if session_state["boosting_results"] is None:
        print("\nrun option 1 first, there's nothing trained yet.")
        return

    # pull the predicted labels and true labels for the model we're auditing
    predicted_labels = session_state["boosting_results"]["predicted_labels"]
    y_test = session_state["y_test"]
    audit_test = session_state["audit_test"]

    # this returns a dictionary with a "race" table and a "gender" table
    audit_tables = run_full_fairness_audit(y_test, predicted_labels, audit_test)

    # print each table with a clear header explaining what the numbers mean
    print("\nfairness audit (gradient boosting model), by race:")
    print("false_negative_rate = fraction of true readmissions the model missed for this group")
    print(audit_tables["race"].to_string(index=False))

    print("\nfairness audit (gradient boosting model), by gender:")
    print(audit_tables["gender"].to_string(index=False))


def score_hypothetical_patient():
    """
    menu option 4: asks the person running the demo a handful of questions about a made
    up patient, then prints that patient's predicted readmission risk from both models
    """
    # guard against running this before training has happened
    if session_state["logistic_pipeline"] is None:
        print("\nrun option 1 first, there's nothing trained yet.")
        return

    print("\nenter a few details about a hypothetical patient at discharge:")
    # input() always returns a string, we keep it as a string since these are categorical
    age_band = input("age band, e.g. [70-80): ") or "[70-80)"  # default value if the user just presses enter
    # int() converts the typed text into a whole number for the numeric fields
    time_in_hospital = int(input("days in hospital (e.g. 4): ") or 4)
    num_lab_procedures = int(input("number of lab procedures (e.g. 45): ") or 45)
    num_medications = int(input("number of medications (e.g. 15): ") or 15)
    number_inpatient = int(input("prior inpatient visits in the last year (e.g. 1): ") or 1)

    # build a single-row dataframe with every column the model expects. any column not
    # asked about above is filled with a reasonable default so the pipeline doesn't error
    patient_row = pd.DataFrame([{
        "time_in_hospital": time_in_hospital,
        "num_lab_procedures": num_lab_procedures,
        "num_procedures": 1,                 # default: a typical patient has at least one procedure
        "num_medications": num_medications,
        "number_outpatient": 0,               # default: no prior outpatient visits
        "number_emergency": 0,                 # default: no prior emergency visits
        "number_inpatient": number_inpatient,
        "number_diagnoses": 7,                  # default: the dataset's typical number of diagnoses
        "age": age_band,
        "admission_type_id": 1,                  # default: emergency admission, the most common type
        "discharge_disposition_id": 1,            # default: discharged to home, the most common outcome
        "admission_source_id": 7,                  # default: admitted via the emergency room
        "diag_1_category": "circulatory",           # default: the most common primary diagnosis category
        "diag_2_category": "diabetes",
        "diag_3_category": "other",
        "insulin": "Steady",
        "change": "No",
        "diabetesMed": "Yes",
        "max_glu_serum": "None",
        "A1Cresult": "None",
    }])

    # ask both trained pipelines for a probability, column 1 is the "readmitted" probability
    logistic_risk = session_state["logistic_pipeline"].predict_proba(patient_row)[0, 1]
    boosting_risk = session_state["boosting_pipeline"].predict_proba(patient_row)[0, 1]

    # print both risk scores as a percentage, easier to read than a raw decimal
    print(f"\nlogistic regression predicted risk: {logistic_risk:.1%}")
    print(f"gradient boosting predicted risk:   {boosting_risk:.1%}")


def print_menu():
    """prints the list of things the person running this script can choose from"""
    print("\nreadmission predictor")
    print("1. train and compare both models")
    print("2. show detailed confusion matrix and classification report")
    print("3. run the fairness audit (race and gender)")
    print("4. score a hypothetical patient")
    print("5. quit")


def main():
    """
    the main loop: show the menu, read a choice, run the matching function, repeat until
    the user chooses to quit
    """
    # a dictionary mapping each menu number to the function that handles it, avoids a
    # long chain of if/elif statements
    menu_actions = {
        "1": train_and_compare_models,
        "2": show_detailed_report,
        "3": run_fairness_audit_option,
        "4": score_hypothetical_patient,
    }

    # loop forever until the user explicitly chooses to quit
    while True:
        print_menu()  # show the options every time through the loop
        choice = input("choose an option: ").strip()  # .strip() removes accidental extra spaces
        if choice == "5":
            print("goodbye.")
            break  # exits the while loop, ending the program
        # .get looks up the chosen function, or None if the input wasn't a valid option
        action = menu_actions.get(choice)
        if action is None:
            print("not a valid option, try again.")
            continue  # skips straight back to showing the menu
        action()  # actually run the function that matches the user's choice


# only run the menu loop when this file is executed directly, not when it's imported
if __name__ == "__main__":
    main()
