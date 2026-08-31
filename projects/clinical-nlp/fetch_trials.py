import json
import urllib.parse
import urllib.request
from typing import List

# pulls live trials straight from the public ClinicalTrials.gov API (v2),
# no api key or account needed, and reshapes each result into the same
# flat dictionary shape used by data/sample_trials.json, so the parser
# never has to know whether a record came from disk or from the network

API_URL = "https://clinicaltrials.gov/api/v2/studies"

# these are the exact field paths the api understands, asking for only
# what is needed keeps each response small and fast to parse
FIELDS = "NCTId,BriefTitle,Condition,EligibilityCriteria,Sex,MinimumAge,MaximumAge"


def fetch_trials(condition: str, page_size: int = 10) -> List[dict]:
    # builds the query string by hand with urlencode, so spaces and special
    # characters in the condition name are escaped correctly
    query = urllib.parse.urlencode({
        "query.cond": condition,
        "pageSize": page_size,
        "fields": FIELDS,
    })
    url = f"{API_URL}?{query}"

    # a real network call, wrapped so the caller gets a clear message
    # instead of a raw traceback if the machine has no internet access
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise RuntimeError(
            f"could not reach clinicaltrials.gov ({error}), "
            "this script needs outbound internet access to fetch live data"
        ) from error

    studies = payload.get("studies", [])
    return [_normalize(study) for study in studies]


def _normalize(study: dict) -> dict:
    # digs the handful of fields actually used out of the deeply nested
    # response shape the api returns, and renames them to match the
    # flat schema the rest of the project expects
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    conditions_module = protocol.get("conditionsModule", {})
    eligibility = protocol.get("eligibilityModule", {})

    return {
        "nct_id": identification.get("nctId", "UNKNOWN"),
        "title": identification.get("briefTitle", ""),
        "conditions": conditions_module.get("conditions", []),
        "known_sex": eligibility.get("sex"),
        "known_minimum_age": eligibility.get("minimumAge"),
        "known_maximum_age": eligibility.get("maximumAge"),
        "eligibility_text": eligibility.get("eligibilityCriteria", ""),
    }


if __name__ == "__main__":
    # a tiny manual smoke test, run this file directly to try a live fetch:
    # python fetch_trials.py
    import sys

    search_term = sys.argv[1] if len(sys.argv) > 1 else "diabetes"
    results = fetch_trials(search_term, page_size=3)
    for trial in results:
        print(trial["nct_id"], "-", trial["title"])
