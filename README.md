# Grant Scanner

Checks GOV.UK's official **Find a Grant** service daily, filters results against
`eligibility_profile.json`, and emails you only the ones that are new and eligible
since the last run.

## What's actually been tested

This environment's network is behind an allowlist that blocks
`find-government-grants.service.gov.uk`, so I can't run the live HTTP fetch
from here. Everything else has been tested against real gov.uk content and one
bug was found and fixed in the process (the closing-date field was extracting
as blank — fixed in `scraper_govuk.py`):

- ✅ Field extraction (`_extract_field`) — tested against real gov.uk grant
  listings in `tests/test_field_extraction.py`. Run it yourself with
  `python3 tests/test_field_extraction.py`.
- ✅ Eligibility matching — tested against both real gov.uk grants and a
  synthetic matching one; correctly accepts/rejects based on location,
  applicant type, and keywords.
- ✅ Email digest formatting — builds correctly from `Grant` objects.
- ✅ New-vs-seen diffing — confirmed a grant only gets flagged as "new" once,
  across simulated repeated runs.
- ⚠️ **Not tested: the live HTTP request and BeautifulSoup card-detection
  against the real page.** This is the one part that needs a run from a
  machine with normal internet access — see step 1 below. If `python main.py`
  reports "Fetched 0 total listings", that's the first place to look: open
  the URL in a browser, inspect a grant card's HTML, and check whether the
  `<li>/<article>/<div>` search in `get_open_grants()` still matches gov.uk's
  actual markup.

## Honest limitations, up front


- **Source coverage:** this scans gov.uk Find a Grant only — the largest single
  official directory of government grants, but not National Lottery, Charity
  Commission-linked trusts, or independent foundations. Those sites don't have a
  public API and each has different markup, so each would need its own scraper
  module added the same way `scraper_govuk.py` was built. This is designed so you
  (or I, in a follow-up) can add `scraper_lottery.py`, `scraper_trusts.py` etc.
  the same way — `main.py` just needs to call them and combine the results.
- **Untested against a live network from this environment** — I built this by
  inspecting the real gov.uk page structure, but I don't have network access to
  run it end-to-end from here. Run it once manually (see below) and check the
  output before trusting the schedule.
- **Cause-area matching is a rough keyword net**, not a clean tag system —
  gov.uk grants don't carry structured cause tags the way National Lottery
  programmes do. Expect to tune `cause_keywords` in the profile after seeing
  what comes through.
- **gov.uk also offers its own free "email me new grants" signup** (no
  eligibility filtering, just literally everything new) — found at the bottom of
  https://www.find-government-grants.service.gov.uk/grants. Worth having running
  alongside this as a backstop.

## 1. Set up locally first (recommended before scheduling anything)

```bash
pip install -r requirements.txt
python main.py
```

The first run will treat every currently-eligible grant as "new" (since
`seen_grants.json` starts empty) — expect one larger digest email, then smaller
day-to-day updates after that.

Before running, set these environment variables (or a `.env` loaded however you
prefer) for the email step:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your-app-password       # not your normal password — see below
ALERT_TO=you@gmail.com
```

For Gmail: turn on 2-Step Verification, then create an **App Password** at
https://myaccount.google.com/apppasswords — use that as `SMTP_PASS`. Any other
provider's SMTP details work the same way.

## 2. Edit your eligibility criteria

Open `eligibility_profile.json` and adjust:
- `acceptable_locations` — which regions count as eligible for you
- `cause_keywords` — words that should appear in a grant's title/summary
- `required_applicant_type` — leave as `"Non-profit"` unless you have a reason to change it

## 3. Schedule it

**Option A — GitHub Actions (recommended, free, no computer needs to stay on)**

1. Push this folder to a new GitHub repository (can be private).
2. In the repo, go to **Settings → Secrets and variables → Actions** and add:
   `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ALERT_TO`.
3. That's it — `.github/workflows/daily-scan.yml` runs it automatically every
   day at 07:00 UTC, and commits the updated `seen_grants.json` back so it
   remembers what it's already shown you. You can also trigger it manually
   from the repo's **Actions** tab any time.

**Option B — cron, if you'd rather run it on your own machine/server**

```
0 7 * * * cd /path/to/grant-scanner && /usr/bin/python3 main.py >> scan.log 2>&1
```

## Files

| File | Purpose |
|---|---|
| `main.py` | Orchestrates the scan → filter → diff → email flow |
| `scraper_govuk.py` | Fetches and parses gov.uk Find a Grant listings |
| `matcher.py` | Applies `eligibility_profile.json` to each grant |
| `notifier.py` | Sends the email digest via SMTP |
| `eligibility_profile.json` | Your criteria — edit this, not the code |
| `seen_grants.json` | Tracks what's already been emailed, so you don't get repeats |
