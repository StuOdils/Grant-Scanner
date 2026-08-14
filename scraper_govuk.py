"""
Scrapes GOV.UK's "Find a grant" service (find-government-grants.service.gov.uk).

This is the official government grants portal. Its listings are published
under the Open Government Licence v3.0, so reading and reusing this data
programmatically is permitted.

NOTE: This was written against the live page structure as of August 2026,
inspected manually. GOV.UK occasionally tweaks the markup of this service.
If get_open_grants() starts returning an empty list despite the site clearly
having results, the CSS selectors below (marked SELECTOR) are the first
place to check — open the page in a browser, right-click a grant card,
"Inspect", and compare against what's here.
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from datetime import datetime
import re
import time

BASE_URL = "https://www.find-government-grants.service.gov.uk/grants"

# fields.grantApplicantType.en-US=4 filters results to schemes open to
# "Non profit" applicants (confirmed against the live filter sidebar).
PARAMS = {
    "fields.grantApplicantType.en-US": "4",
    "limit": "20",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CharityGrantScanner/1.0; personal research tool)"
}


@dataclass
class Grant:
    title: str
    url: str
    funder: str
    location: str
    who_can_apply: str
    amount_text: str
    closing_date_text: str
    summary: str

    def as_dict(self):
        return asdict(self)


def _extract_field(block_text: str, label: str, next_labels: list[str]) -> str:
    """
    GOV.UK renders each grant card as a stack of label/value pairs
    (e.g. "Location\\nEngland"). We find the label, then take everything
    up to whichever of next_labels appears first (or to the end of the
    block if next_labels is empty).
    """
    if next_labels:
        lookahead = "(?=" + "|".join(re.escape(l) for l in next_labels) + r"|$)"
    else:
        lookahead = r"$"
    pattern = re.escape(label) + r"\s*(.*?)" + lookahead
    match = re.search(pattern, block_text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _parse_card(card) -> Grant | None:
    link = card.find("a", href=True)
    if not link or "/grants/" not in link["href"]:
        return None

    title = link.get_text(strip=True)
    url = link["href"]
    if url.startswith("/"):
        url = "https://www.find-government-grants.service.gov.uk" + url

    text = card.get_text("\n", strip=True)

    labels_in_order = [
        "Funding organisation", "Who can apply", "Location",
        "How much you can get", "Total size of grant scheme",
        "Opening date", "Closing date"
    ]

    funder = _extract_field(text, "Funding organisation", labels_in_order)
    who = _extract_field(text, "Who can apply", labels_in_order)
    location = _extract_field(text, "Location", labels_in_order)
    amount = _extract_field(text, "How much you can get", labels_in_order)
    closing = _extract_field(text, "Closing date", [])

    # Summary = whatever text sits between the title and "Location"
    summary_match = re.search(re.escape(title) + r"(.*?)Location", text, re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else ""

    return Grant(
        title=title, url=url, funder=funder, location=location,
        who_can_apply=who, amount_text=amount,
        closing_date_text=closing, summary=summary[:400]
    )


def get_open_grants(max_pages: int = 6, delay_seconds: float = 1.0) -> list[Grant]:
    """
    Fetches grant listings across up to max_pages of results (20 per page).
    Stops early once a page returns no cards, OR once a page returns nothing
    but URLs we've already seen (which means the 'skip' pagination parameter
    isn't actually moving forward — seen live: gov.uk returned the same 20
    grants 6 times over, which without this check would have produced the
    same grant appearing 6 times in the final list).
    """
    grants: list[Grant] = []
    seen_urls: set[str] = set()   # global across ALL pages, not just one
    skip = 0

    for _ in range(max_pages):
        params = dict(PARAMS)
        params["skip"] = str(skip)

        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # SELECTOR: grant cards are list items containing a link into /grants/<slug>
        candidate_blocks = soup.find_all(["li", "article", "div"], recursive=True)
        page_grants = []
        seen_urls_this_page = set()
        for block in candidate_blocks:
            g = _parse_card(block)
            if g and g.url not in seen_urls_this_page:
                # avoid double-counting nested containers matching the same link
                if not any(g.url == existing.url for existing in page_grants):
                    page_grants.append(g)
                    seen_urls_this_page.add(g.url)

        if not page_grants:
            break

        # Only keep grants we haven't seen on an earlier page.
        new_this_page = [g for g in page_grants if g.url not in seen_urls]

        if not new_this_page:
            # Every grant on this "page" was already seen before — the skip
            # parameter isn't actually advancing pagination. Stop here
            # rather than looping max_pages times over identical results.
            break

        grants.extend(new_this_page)
        seen_urls.update(g.url for g in new_this_page)
        skip += 20
        time.sleep(delay_seconds)

    return grants


if __name__ == "__main__":
    results = get_open_grants(max_pages=1)
    print(f"Fetched {len(results)} grant(s) from page 1.")
    for g in results[:5]:
        print("-", g.title, "|", g.location, "|", g.amount_text)
