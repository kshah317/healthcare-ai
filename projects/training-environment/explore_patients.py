# explore_patients.py
#
# a first look at the fake patients that generate_patients.py makes. it reads the csv tables
# synthea wrote (patients, conditions, medications, encounters) and prints a short summary:
# how many people, the gender split, ages, the most common diagnoses and prescriptions, and
# how many doctor visits each person had.
#
# this is the "now what do i do with all this data" step, so it stays small on purpose. it is
# a starting point to build on, not an analysis.
#
# usage:
#   python generate_patients.py       # make some fake patients first
#   python explore_patients.py        # then take a look at them

import sys
from datetime import date
from pathlib import Path

import pandas as pd

# the folder generate_patients.py fills up, resolved next to this file so it works from anywhere
CSV_DIR = Path(__file__).resolve().parent / "generated-patients" / "csv"

# the four synthea tables this script reads
TABLE_NAMES = ["patients", "conditions", "medications", "encounters"]


def load_tables(csv_dir=CSV_DIR):
    # reads each table into a pandas dataframe, keyed by its name
    csv_dir = Path(csv_dir)

    # nothing generated yet, so point the reader at the step they skipped
    if not csv_dir.exists():
        raise FileNotFoundError(
            f"no patient files found at {csv_dir}. run python generate_patients.py first."
        )

    tables = {}
    for name in TABLE_NAMES:
        path = csv_dir / f"{name}.csv"

        # synthea always writes these four, so a missing one means the run was cut short
        if not path.exists():
            raise FileNotFoundError(f"expected {path} but it is missing, try generating again")
        tables[name] = pd.read_csv(path)
    return tables


def ages_of_living_patients(patients, today):
    # age in whole years as of today, only for people who have no death date
    living = patients[patients["DEATHDATE"].isna()]
    birthdays = pd.to_datetime(living["BIRTHDATE"])

    # subtract the year, then take one off if the birthday hasn't happened yet this year
    had_birthday = (birthdays.dt.month < today.month) | (
        (birthdays.dt.month == today.month) & (birthdays.dt.day <= today.day)
    )
    return today.year - birthdays.dt.year - (~had_birthday).astype(int)


def top_by_patients(table, top=5):
    # most common descriptions, counting each patient once so one frequent flyer can't dominate
    counts = table.groupby("DESCRIPTION")["PATIENT"].nunique()
    return counts.sort_values(ascending=False).head(top)


def summarize(tables, today=None):
    # boils the four tables down to a handful of numbers and short lists
    today = today or date.today()
    patients = tables["patients"]
    ages = ages_of_living_patients(patients, today)

    # visits per person, counting people with zero visits too
    visits = tables["encounters"].groupby("PATIENT").size()
    visits = visits.reindex(patients["Id"], fill_value=0)

    return {
        "patients": len(patients),
        "living": int(patients["DEATHDATE"].isna().sum()),
        "gender": patients["GENDER"].value_counts().to_dict(),
        "age_min": int(ages.min()) if len(ages) else None,
        "age_median": float(ages.median()) if len(ages) else None,
        "age_max": int(ages.max()) if len(ages) else None,
        "top_conditions": top_by_patients(tables["conditions"]).to_dict(),
        "top_medications": top_by_patients(tables["medications"]).to_dict(),
        "visits_median": float(visits.median()),
        "visits_max": int(visits.max()),
    }


def print_summary(summary):
    # prints the summary in plain words
    print(f"{summary['patients']} fake patients ({summary['living']} still alive)")
    print("gender split:", ", ".join(f"{k}: {v}" for k, v in summary["gender"].items()))

    # age line only makes sense if anyone is alive
    if summary["age_median"] is not None:
        print(
            f"ages of living patients: youngest {summary['age_min']}, "
            f"median {summary['age_median']:.0f}, oldest {summary['age_max']}"
        )

    print(
        f"doctor visits per person: median {summary['visits_median']:.0f}, "
        f"most {summary['visits_max']}"
    )

    print("\nmost common diagnoses (number of patients):")
    for name, count in summary["top_conditions"].items():
        print(f"  {count:>4}  {name}")

    print("\nmost common medications (number of patients):")
    for name, count in summary["top_medications"].items():
        print(f"  {count:>4}  {name}")


def main():
    # friendly message instead of a traceback when the data isn't there yet
    try:
        tables = load_tables()
    except FileNotFoundError as error:
        print(error)
        return 1

    print_summary(summarize(tables))
    return 0


if __name__ == "__main__":
    sys.exit(main())
