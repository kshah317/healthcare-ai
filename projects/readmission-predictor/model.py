"""
this file builds, trains, and scores the two models this project compares: a logistic
regression that is easy to explain, and a gradient-boosted tree model that trades some
of that explainability for accuracy. both models share the exact same preprocessing
steps, so the only thing that differs between them is the model itself, which is what
makes the comparison fair.
"""

# numpy gives us array operations, used here mostly for threshold math
import numpy as np
# ColumnTransformer lets us apply different preprocessing to different columns at once
from sklearn.compose import ColumnTransformer
# Pipeline chains preprocessing and a model together so they always run in the same order
from sklearn.pipeline import Pipeline
# OneHotEncoder turns a categorical column into a set of 0/1 columns the model can read
# StandardScaler rescales numeric columns to have mean 0 and standard deviation 1
from sklearn.preprocessing import OneHotEncoder, StandardScaler
# SimpleImputer fills in missing values, since a handful of our columns still have gaps
# even after cleaning (e.g. a diagnosis category that legitimately doesn't apply)
from sklearn.impute import SimpleImputer
# LogisticRegression is our interpretable, explainable baseline model
from sklearn.linear_model import LogisticRegression
# HistGradientBoostingClassifier is scikit-learn's built-in gradient boosted tree model,
# chosen specifically because it ships with scikit-learn already, so this project doesn't
# need an extra dependency like xgboost just to get a stronger model
from sklearn.ensemble import HistGradientBoostingClassifier
# these are the evaluation metrics we use instead of plain accuracy, explained in the readme
from sklearn.metrics import roc_auc_score, average_precision_score, confusion_matrix, classification_report

# importing our own column lists from preprocess.py so model.py and preprocess.py never
# disagree about which columns are numeric vs categorical
from preprocess import NUMERIC_FEATURE_COLUMNS, CATEGORICAL_FEATURE_COLUMNS


def build_preprocessing_step():
    """
    builds the ColumnTransformer that both models share. numeric columns get missing
    values filled with the median and then scaled, categorical columns get missing
    values filled with a placeholder string and then one-hot encoded
    """
    # numeric_transformer is its own small pipeline: impute first, then scale
    numeric_transformer = Pipeline(steps=[
        ("impute", SimpleImputer(strategy="median")),  # fills any numeric gaps with the median value
        ("scale", StandardScaler()),                    # puts every numeric column on the same scale
    ])
    # categorical_transformer is its own small pipeline: impute first, then one-hot encode
    categorical_transformer = Pipeline(steps=[
        ("impute", SimpleImputer(strategy="constant", fill_value="missing")),  # fills gaps with the literal string "missing"
        # handle_unknown="ignore" means an unseen category at prediction time is ignored instead of crashing.
        # sparse_output=False forces a normal dense array, since the gradient boosting model
        # below can't accept the sparse matrix format OneHotEncoder uses by default
        ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    # ColumnTransformer applies numeric_transformer to the numeric columns and
    # categorical_transformer to the categorical columns, then glues the results back together
    preprocessing = ColumnTransformer(transformers=[
        ("numeric", numeric_transformer, NUMERIC_FEATURE_COLUMNS),        # applies to our numeric column list
        ("categorical", categorical_transformer, CATEGORICAL_FEATURE_COLUMNS),  # applies to our categorical column list
    ])
    # hand back the assembled preprocessing step, ready to be put in a Pipeline
    return preprocessing


def build_logistic_regression_pipeline():
    """
    builds the full pipeline for the interpretable baseline model: shared preprocessing,
    followed by logistic regression. class_weight="balanced" tells the model to pay more
    attention to the rare positive class instead of just predicting "no" for everyone,
    which is important since only about 1 in 9 encounters is an actual <30 day readmission
    """
    pipeline = Pipeline(steps=[
        ("preprocessing", build_preprocessing_step()),  # the shared cleaning/encoding step
        ("model", LogisticRegression(
            class_weight="balanced",  # upweights the rare positive class during training
            max_iter=1000,            # gives the optimizer enough steps to actually converge
            random_state=42,          # makes the training run reproducible
        )),
    ])
    # hand back the unfitted pipeline, ready to be trained with .fit()
    return pipeline


def build_gradient_boosting_pipeline():
    """
    builds the full pipeline for the stronger comparison model: the same shared
    preprocessing, followed by a gradient boosted tree classifier
    """
    pipeline = Pipeline(steps=[
        ("preprocessing", build_preprocessing_step()),  # identical preprocessing to the logistic regression pipeline
        ("model", HistGradientBoostingClassifier(
            class_weight="balanced",  # same imbalance handling as the logistic regression model
            random_state=42,          # makes the training run reproducible
        )),
    ])
    # hand back the unfitted pipeline, ready to be trained with .fit()
    return pipeline


def train_pipeline(pipeline, X_train, y_train):
    """
    trains a given pipeline on the training data and returns the now-fitted pipeline.
    this is a thin wrapper so cli.py doesn't need to know the scikit-learn method name
    """
    # .fit() runs the preprocessing and then trains the model, all in one call
    pipeline.fit(X_train, y_train)
    # hand back the same pipeline object, now trained
    return pipeline


def evaluate_pipeline(pipeline, X_test, y_test, threshold=0.5):
    """
    scores a trained pipeline against the held-out test set and returns a dictionary of
    metrics. accuracy is deliberately not included here, since with only about 11% of
    rows being positive, a model that always predicts "no" would score about 89% accuracy
    while being completely useless
    """
    # predict_proba returns a probability for each class, column 1 is the probability of
    # the positive class, i.e. "this patient will be readmitted within 30 days"
    predicted_probabilities = pipeline.predict_proba(X_test)[:, 1]
    # turn the probabilities into 0/1 predictions using the chosen decision threshold
    predicted_labels = (predicted_probabilities >= threshold).astype(int)

    # roc_auc_score measures how well the model ranks positives above negatives across
    # every possible threshold, 0.5 is random guessing and 1.0 is perfect separation
    roc_auc = roc_auc_score(y_test, predicted_probabilities)
    # average_precision_score is the area under the precision-recall curve, more
    # informative than roc_auc when the positive class is rare, like it is here
    pr_auc = average_precision_score(y_test, predicted_probabilities)
    # confusion_matrix breaks predictions down into true/false positives/negatives at
    # the chosen threshold, which is what the fairness audit builds on
    matrix = confusion_matrix(y_test, predicted_labels)
    # classification_report gives precision, recall, and f1 in one readable block of text
    report_text = classification_report(y_test, predicted_labels, zero_division=0)

    # bundle every metric into one dictionary so the caller only needs to keep track of one object
    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "confusion_matrix": matrix,
        "classification_report": report_text,
        "predicted_probabilities": predicted_probabilities,  # kept for the fairness audit and threshold experiments
        "predicted_labels": predicted_labels,                # kept for the fairness audit
    }
