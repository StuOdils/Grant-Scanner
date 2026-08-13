"""Applies eligibility_profile.json to a list of scraped Grant objects."""

from scraper_govuk import Grant


def is_eligible(grant: Grant, profile: dict) -> tuple[bool, list[str]]:
    reasons_failed = []

    # Applicant type
    if profile["required_applicant_type"].lower() not in grant.who_can_apply.lower():
        reasons_failed.append(f"Not listed as open to {profile['required_applicant_type']} applicants")

    # Location
    acceptable = [loc.lower() for loc in profile["acceptable_locations"]]
    if not any(loc in grant.location.lower() for loc in acceptable):
        reasons_failed.append(f"Location '{grant.location}' not in your accepted regions")

    # Cause keywords (skipped entirely if the list is empty)
    keywords = [k.lower() for k in profile.get("cause_keywords", [])]
    if keywords:
        haystack = f"{grant.title} {grant.summary}".lower()
        if not any(k in haystack for k in keywords):
            reasons_failed.append("No keyword match in title or summary")

    return (len(reasons_failed) == 0, reasons_failed)


def filter_eligible(grants: list[Grant], profile: dict) -> list[Grant]:
    eligible = []
    for g in grants:
        ok, _ = is_eligible(g, profile)
        if ok:
            eligible.append(g)
    return eligible
