# check_no_real_data.py
#
# a safety net that scans files before they get committed and complains if anything looks like
# real patient data or a secret. the patients in this project are all fake (made by synthea), so
# the point isn't to catch fake data, it's to make sure a real record or a password never slips
# into the repo by accident, either from my laptop or from an edit in the github web editor.
#
# usage:
#   python check_no_real_data.py                  # checks every file git is tracking
#   python check_no_real_data.py a.py b.csv       # checks only the files you pass in
#
# exit code is 0 when everything is clean and 1 when something looks wrong, which is what
# pre-commit and github actions use to decide whether to stop.

import re
import subprocess
import sys
from pathlib import Path

# files that are allowed to contain the scary-looking patterns because they define or test them
SELF_FILES = {"check_no_real_data.py", "test_check_no_real_data.py"}

# any file bigger than this is skipped, it's almost certainly not hand-written text
MAX_BYTES = 2_000_000

# file names and extensions that should never be committed no matter what is inside them
BLOCKED_SUFFIXES = (".env", ".pem", ".key", ".jar")
BLOCKED_FOLDERS = ("generated-patients",)

# patterns that look like real identifiers or secrets, each with a plain-english label
CONTENT_RULES = [
    ("social security number", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("medical record number", re.compile(r"\bmrn\s*[:#=]?\s*\d{6,}\b", re.IGNORECASE)),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "hardcoded secret",
        re.compile(
            r"(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]([^'\"\s]{8,})['\"]",
            re.IGNORECASE,
        ),
    ),
]

# values that are clearly placeholders, so "password = 'your-password-here'" isn't a false alarm
PLACEHOLDER_HINTS = ("example", "changeme", "your", "xxx", "placeholder", "<", "${")


def is_placeholder(text):
    # lowercase once so the hint check ignores capitalization
    lowered = text.lower()
    return any(hint in lowered for hint in PLACEHOLDER_HINTS)


def check_path(path):
    # returns a list of problems based only on the file's name and location
    problems = []
    posix = Path(path).as_posix()

    # blocked extensions like .env or .pem
    if posix.endswith(BLOCKED_SUFFIXES):
        problems.append(f"{posix}: this kind of file should never be committed")

    # anything sitting inside the generated patients folder
    for folder in BLOCKED_FOLDERS:
        if f"{folder}/" in posix or posix.startswith(folder):
            problems.append(f"{posix}: generated patient data should stay out of git")
    return problems


def check_text(name, text):
    # returns a list of problems found inside the text of one file
    problems = []

    # go line by line so each finding can point at an exact line number
    for line_number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in CONTENT_RULES:
            match = pattern.search(line)

            # no match for this rule on this line, move on
            if not match:
                continue

            # for the secret rule, ignore obvious placeholder values
            if label == "hardcoded secret" and is_placeholder(match.group(2)):
                continue

            problems.append(f"{name}:{line_number}: looks like a {label}")
    return problems


def check_file(path):
    # runs both the name checks and the content checks on one file
    path = Path(path)
    problems = check_path(path)

    # the checker and its tests are allowed to mention the patterns they look for
    if path.name in SELF_FILES:
        return problems

    # skip things that aren't regular files (deleted files show up in some git listings)
    if not path.is_file():
        return problems

    # skip huge files, they aren't hand-written
    if path.stat().st_size > MAX_BYTES:
        return problems

    # binary files can't be decoded as text, so there's nothing to scan
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return problems

    return problems + check_text(path.as_posix(), text)


def tracked_files():
    # asks git for every file it is tracking, so the scan matches what would be pushed
    result = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def main(argv):
    # use the files passed in, or fall back to everything git tracks
    files = argv or tracked_files()

    problems = []
    for file in files:
        problems.extend(check_file(file))

    # clean run
    if not problems:
        print(f"checked {len(files)} file(s), nothing suspicious")
        return 0

    # something looked wrong, list it all and fail so the commit or the pull request stops
    print("found things that should not be committed:")
    for problem in problems:
        print(f"  {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
