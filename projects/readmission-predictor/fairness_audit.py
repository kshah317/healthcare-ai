"""
this file checks whether the model's mistakes are spread evenly across race and gender
groups, even though the model was never given race or gender as inputs. a model can
still end up less accurate for one group than another if the features it does use
happen to correlate with race or gender in the training data, this is usually called
proxy discrimination. the only way to catch that is to check the outcomes directly,
which is what this file does.
"""

# pandas is used to group the results by subgroup and build the summary table
import pandas as pd


def compute_subgroup_error_rates(y_true, predicted_labels, subgroup_values):
    """
    for a single categorical attribute (e.g. race), this computes the false negative
    rate, false positive rate, and recall for every value that attribute takes (e.g.
    "Caucasian", "AfricanAmerican", and so on).

    a false negative here means: this patient really was readmitted within 30 days, but
    the model said they were low risk. that's the more dangerous kind of error in a
    healthcare setting, since it means a patient who needed extra follow-up didn't get
    flagged for it.
    """
    # combine the true labels, the model's predictions, and the subgroup labels into one
    # small dataframe so we can group by subgroup easily
    results_df = pd.DataFrame({
        "y_true": y_true.reset_index(drop=True),                # the real outcome, reindexed so it lines up by position
        "y_pred": pd.Series(predicted_labels),                   # the model's 0/1 prediction
        "subgroup": subgroup_values.reset_index(drop=True),      # which race/gender group this row belongs to
    })

    # this list will hold one row of results per subgroup value, turned into a table at the end
    subgroup_rows = []

    # .unique() gives every distinct value the subgroup column takes, e.g. every race listed
    for subgroup_value in results_df["subgroup"].unique():
        # slice down to just the rows belonging to this one subgroup
        group_df = results_df[results_df["subgroup"] == subgroup_value]

        # actual_positive_count is how many people in this group were really readmitted within 30 days
        actual_positive_count = (group_df["y_true"] == 1).sum()
        # actual_negative_count is how many people in this group were not readmitted within 30 days
        actual_negative_count = (group_df["y_true"] == 0).sum()

        # false_negative_count: model said "low risk" (0) but the patient was actually readmitted (1)
        false_negative_count = ((group_df["y_true"] == 1) & (group_df["y_pred"] == 0)).sum()
        # false_positive_count: model said "high risk" (1) but the patient was not actually readmitted (0)
        false_positive_count = ((group_df["y_true"] == 0) & (group_df["y_pred"] == 1)).sum()
        # true_positive_count: model correctly said "high risk" and the patient was readmitted
        true_positive_count = ((group_df["y_true"] == 1) & (group_df["y_pred"] == 1)).sum()

        # false negative rate: of the people who really were readmitted, what fraction did the model miss?
        # guarded with an if to avoid dividing by zero if a subgroup has no actual positives
        false_negative_rate = false_negative_count / actual_positive_count if actual_positive_count > 0 else float("nan")
        # false positive rate: of the people who were not readmitted, what fraction did the model wrongly flag?
        false_positive_rate = false_positive_count / actual_negative_count if actual_negative_count > 0 else float("nan")
        # recall: of the people who really were readmitted, what fraction did the model correctly catch?
        recall = true_positive_count / actual_positive_count if actual_positive_count > 0 else float("nan")

        # add one row of summary numbers for this subgroup to our results list
        subgroup_rows.append({
            "subgroup": subgroup_value,                 # e.g. "Caucasian" or "Female"
            "n": len(group_df),                          # how many rows (encounters) belong to this subgroup
            "actual_positive_count": actual_positive_count,  # how many were really readmitted within 30 days
            "false_negative_rate": false_negative_rate,  # missed-risk rate, the more dangerous error
            "false_positive_rate": false_positive_rate,  # over-flagged rate, the more wasteful error
            "recall": recall,                             # fraction of true positives the model actually caught
        })

    # turn the list of per-subgroup dictionaries into a single, easy-to-read dataframe
    summary_df = pd.DataFrame(subgroup_rows)
    # sort by subgroup size, biggest group first, purely to make the printed table easier to scan
    summary_df = summary_df.sort_values("n", ascending=False).reset_index(drop=True)
    # hand back the finished summary table
    return summary_df


def run_full_fairness_audit(y_test, predicted_labels, audit_test):
    """
    runs compute_subgroup_error_rates once per audited attribute (race, then gender) and
    returns both tables together in a dictionary, so cli.py can print them one after another
    """
    # build the race breakdown
    race_summary = compute_subgroup_error_rates(y_test, predicted_labels, audit_test["race"])
    # build the gender breakdown
    gender_summary = compute_subgroup_error_rates(y_test, predicted_labels, audit_test["gender"])
    # hand back both tables in one dictionary
    return {"race": race_summary, "gender": gender_summary}
