"""
generate a batch of fake (synthetic) patient records with synthea and tidy up the results.

synthea is an open source java program that invents realistic but completely made-up
patients: names, birthdays, doctor visits, diagnoses, prescriptions, and so on. since
none of these people exist, there's zero privacy risk, but the records look enough like
the real thing to practice on.

this script does three things:
  1. makes sure the synthea jar file is available (downloads it once if it's missing)
  2. runs synthea to generate however many patients you ask for
  3. moves the output into a predictable folder, generated-patients/, sorted by format
     (csv/ for spreadsheet-style tables, fhir/ for the json healthcare standard format)

usage:
  python generate_patients.py              # generates 10 patients
  python generate_patients.py --count 50   # generates 50 patients
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

# everything is resolved relative to this file, so the script works from any directory
PROJECT_DIR = Path(__file__).resolve().parent
JAR_PATH = PROJECT_DIR / "synthea-with-dependencies.jar"
OUTPUT_DIR = PROJECT_DIR / "generated-patients"

# synthea publishes a rolling "latest" build of the jar at this stable address
JAR_URL = (
    "https://github.com/synthetichealth/synthea/releases/download/"
    "master-branch-latest/synthea-with-dependencies.jar"
)


def ensure_jar(jar_path=JAR_PATH, url=JAR_URL):
    """download the synthea jar if it isn't already sitting next to this script."""
    # skip the download if we already have it from a previous run
    if jar_path.exists():
        return jar_path

    print("synthea jar not found, downloading it (about 200 mb, one time only)...")
    print(f"  from: {url}")
    try:
        urllib.request.urlretrieve(url, jar_path)
    except Exception as err:
        # clean up a half-downloaded file so the next run doesn't think it's valid
        if jar_path.exists():
            jar_path.unlink()
        sys.exit(
            "couldn't download synthea automatically.\n"
            f"  reason: {err}\n"
            f"  fix: grab it by hand from {url}\n"
            f"  and save it as {jar_path}"
        )
    return jar_path


def check_java():
    """stop early with a friendly message if java isn't installed."""
    # shutil.which comes back empty when the command isn't on the path
    if shutil.which("java") is None:
        sys.exit(
            "java isn't installed or isn't on your path, and synthea needs it to run.\n"
            "  if you're inside the dev container this should already be set up,\n"
            "  so try rebuilding the container."
        )


def run_synthea(count, work_dir, jar_path=JAR_PATH):
    """run synthea inside work_dir so its raw output lands there, not in the project."""
    command = [
        "java",
        "-jar",
        str(jar_path),
        "-p",
        str(count),
        # csv export is off by default in synthea, this turns it on alongside fhir
        "--exporter.csv.export=true",
    ]
    print(f"running synthea for {count} patients, this can take a minute...")
    result = subprocess.run(command, cwd=work_dir)
    # a nonzero exit code means synthea itself hit a problem
    if result.returncode != 0:
        sys.exit(f"synthea exited with an error (code {result.returncode}).")


def organize_output(raw_output_dir, dest_dir=OUTPUT_DIR):
    """
    move synthea's raw output into a clean, predictable layout.

    synthea writes to output/csv/ and output/fhir/ (plus a few other folders depending on
    its settings). this moves just the csv and fhir files into dest_dir/csv and
    dest_dir/fhir, replacing whatever was there from the last run so results never mix.
    returns a dict of how many files landed in each folder.
    """
    raw_output_dir = Path(raw_output_dir)
    dest_dir = Path(dest_dir)
    counts = {"csv": 0, "fhir": 0}

    # bail out clearly if synthea didn't produce anything to organize
    if not raw_output_dir.exists():
        raise FileNotFoundError(f"no synthea output found at {raw_output_dir}")

    for kind, pattern in (("csv", "*.csv"), ("fhir", "*.json")):
        source = raw_output_dir / kind
        target = dest_dir / kind

        # skip formats synthea didn't generate this time
        if not source.exists():
            continue

        # wipe the previous batch so old and new patients don't get mixed together
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)

        # move each matching file over and keep a running count
        for file in sorted(source.glob(pattern)):
            shutil.move(str(file), str(target / file.name))
            counts[kind] += 1

    return counts


def main():
    parser = argparse.ArgumentParser(description="generate fake patients with synthea")
    parser.add_argument(
        "--count", type=int, default=10, help="how many patients to generate (default 10)"
    )
    args = parser.parse_args()

    # synthea needs at least one patient to do anything useful
    if args.count < 1:
        sys.exit("--count needs to be at least 1.")

    check_java()
    jar_path = ensure_jar()

    # use a throwaway folder for synthea's raw output, it's deleted automatically after
    with tempfile.TemporaryDirectory() as work_dir:
        run_synthea(args.count, work_dir, jar_path)
        counts = organize_output(Path(work_dir) / "output")

    print(f"done! results are in {OUTPUT_DIR}")
    print(f"  csv files:  {counts['csv']}")
    print(f"  fhir files: {counts['fhir']}")


# only run when called as a script, not when imported by the tests
if __name__ == "__main__":
    main()
