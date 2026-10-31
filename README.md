# reviews-to-sheets

Opens the review pages of [web-scraping.dev](https://web-scraping.dev) in a real browser (Playwright), loads everything and writes it to a Google Sheet. Running it again only adds the reviews that aren't in the sheet yet, so it can run every day and the sheet keeps growing without duplicates.

The two pages can't be scraped with plain requests because the data isn't in the html:

| Page | How it loads | What the scraper does |
|---|---|---|
| `/reviews` | 20 reviews from a GraphQL api, then a **Load More** button | clicks the button until it disappears (4 clicks, 96 reviews) |
| `/testimonials` | infinite scroll, the next 10 load when you reach the bottom (htmx) | scrolls to the last one until nothing new loads (60 testimonials) |

After the page is fully loaded the html is parsed with BeautifulSoup. Images and fonts are blocked to make it faster, and if something fails (page changed, timeout) a screenshot is saved to `output/error.png`.

## Google Sheet

The sheet gets 4 tabs, created on the first run:

- **Reviews** - review id, product, date, rating (1-5), text, first seen
- **Testimonials** - id, rating, text, first seen
- **Summary** - one row per product: number of reviews, average rating, count of 5 / 4 / 3 / 2 / 1 star reviews, latest review and the lowest rated one. Rewritten every run
- **Runs** - one line per run with how many were found and how many were new

The same data is also saved as csv in `output/` (also when you don't use Google Sheets).

```
96 reviews (5 pages)
60 testimonials
Ratings: 5* 51, 4* 30, 3* 14, 2* 1, 1* 0
Saved reviews.csv, testimonials.csv and summary.csv to output/
Google Sheet "Reviews tracker": 96 new reviews, 60 new testimonials
```

Next run, when nothing changed on the site:

```
Google Sheet "Reviews tracker": 0 new reviews, 0 new testimonials
```

## Setup

```
pip install -r requirements.txt
python -m playwright install chromium
```

Needs Python 3.10 or newer. On a Mac use `python3` instead of `python`.

### Google service account

1. In [Google Cloud Console](https://console.cloud.google.com/) create a project and enable the **Google Sheets API**
2. APIs & Services > Credentials > Create credentials > **Service account**
3. Open the service account > Keys > Add key > JSON. Save the file as `credentials.json` in this folder (it's in `.gitignore`)
4. Create a Google Sheet and share it with the service account email (`...@...iam.gserviceaccount.com`) as Editor
5. Copy the sheet id from the url: `docs.google.com/spreadsheets/d/<this part>/edit`

## Usage

```
python main.py --sheet-id 1AbC...xyz
python main.py --no-sheets          # only the csv files
python main.py --headed             # watch the browser do it
```

`SHEET_ID` and `GOOGLE_CREDENTIALS` (path to the json) can also be set as environment variables.

### Running it every day

With cron (`crontab -e`):

```
0 7 * * * cd /path/to/reviews-to-sheets && /usr/bin/python3 main.py >> scrape.log 2>&1
```

Or with GitHub Actions, see `.github/workflows/scrape.yml`. It runs every day at 06:00 UTC (and with the "Run workflow" button). Add two repository secrets: `SHEET_ID`, and `GOOGLE_CREDENTIALS_JSON` with the content of the json file. The csv files and the error screenshot are uploaded as an artifact of the run.

## Tests

```
pip install pytest
python -m pytest
```

The tests run the real browser against a local copy of the two pages (`tests/fake_site.py`) that loads the data the same way with javascript: a Load More button with a json api and an infinite scroll. Google Sheets is replaced by a small fake (`tests/fake_gspread.py`) to check that a second run doesn't add duplicates.

Built with Playwright, BeautifulSoup, gspread and pandas.
