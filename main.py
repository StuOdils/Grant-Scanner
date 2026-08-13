import json
import os
import sys

from scraper_govuk import get_open_grants
from matcher import filter_eligible
from notifier import send_digest

PROFILE_PATH = "eligibility_profile.json"
STATE_PATH = "seen_grants.json"


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    profile = load_json(PROFILE_PATH, None)
    if profile is None:
        print(f"Missing {PROFILE_PATH} — copy it from the repo and edit your criteria.")
        sys.exit(1)

    seen = set(load_json(STATE_PATH, []))

    print("Fetching current grants from gov.uk Find a Grant...")
    all_grants = get_open_grants(max_pages=6)
    print(f"Fetched {len(all_grants)} total listings open to non-profits.")

    eligible = filter_eligible(all_grants, profile)
    print(f"{len(eligible)} pass your eligibility criteria.")
    for g in eligible:
        print(f"  - {g.title} | {g.funder} | {g.amount_text} | {g.url}")

    new_eligible = [g for g in eligible if g.url not in seen]
    print(f"{len(new_eligible)} of those are new since the last run.")

    send_digest(new_eligible)

    # Record everything eligible we've now shown the user, so re-runs
    # only alert on genuinely new opportunities.
    seen.update(g.url for g in eligible)
    save_json(STATE_PATH, sorted(seen))


if __name__ == "__main__":
    main()
