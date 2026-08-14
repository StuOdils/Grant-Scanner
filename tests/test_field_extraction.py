"""
Offline sanity test for the field-extraction logic in scraper_govuk.py.

This does NOT test the live HTTP request or the BeautifulSoup card-detection
step (both need real network access to the actual site, which this sandbox
can't reach). What it DOES prove: given real gov.uk text content, the label
extraction regex correctly pulls out funder / location / amount / dates.

Run with: python3 tests/test_field_extraction.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper_govuk import _extract_field

LABELS_IN_ORDER = [
    "Funding organisation", "Who can apply", "Location",
    "How much you can get", "Total size of grant scheme",
    "Opening date", "Closing date"
]

with open(os.path.join(os.path.dirname(__file__), "fixture_govuk_sample.txt"), encoding="utf-8") as f:
    fixture = f.read()

blocks = fixture.split("## [")[1:]  # split into per-grant chunks

expected = [
    {
        "title": "National River Walks",
        "Funding organisation": "Department for Environment Food and Rural Affairs",
        "Location": "England",
        "How much you can get": "From £1 to £1.35 million",
        "Closing date": "27 August 2026, 12:00pm (Midday)",
    },
    {
        "title": "Barnsley AI Upskilling Fund",
        "Funding organisation": "Department for Science, Innovation and Technology",
        "Location": "North West England",
        "How much you can get": "From £100,000 to £350,000",
        "Closing date": "12 August 2026, 5:00pm",
    },
]

passed = 0
failed = 0

for block, exp in zip(blocks, expected):
    text = "## [" + block
    print(f"\n--- {exp['title']} ---")
    for label in ["Funding organisation", "Location", "How much you can get"]:
        result = _extract_field(text, label, LABELS_IN_ORDER)
        ok = result == exp[label]
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {label}: got={result!r} expected={exp[label]!r}")

    # Closing date has nothing after it in the block, so pass empty next_labels
    closing = _extract_field(text, "Closing date", [])
    ok = closing == exp["Closing date"]
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  [{status}] Closing date: got={closing!r} expected={exp['Closing date']!r}")

print(f"\n{passed} passed, {failed} failed.")
sys.exit(1 if failed else 0)
