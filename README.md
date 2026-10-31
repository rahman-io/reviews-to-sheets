# reviews-to-sheets

Scraper for the reviews and testimonials pages on web-scraping.dev. Both pages load the data with javascript (a "Load More" button on /reviews and infinite scroll on /testimonials), so I used Playwright to open them in a browser, load everything and then parse the html with BeautifulSoup.

The data goes to a Google Sheet. When you run it again it only adds the reviews that are not in the sheet yet, so it can run every day without duplicates. It also saves csv files in the output folder.

Sheet tabs: Reviews, Testimonials, Summary (per product: avg rating, stars count, lowest rated review) and Runs (log of every run).

## Install

```
pip install -r requirements.txt
python -m playwright install chromium
```

## Google Sheets

You need a service account json from Google Cloud (enable Google Sheets API, create a service account, add a JSON key). Save it as credentials.json in this folder and share your sheet with the service account email.

## Run

```
python main.py --sheet-id YOUR_SHEET_ID
```

Without Google Sheets, only csv:

```
python main.py --no-sheets
```

Add `--headed` if you want to see the browser.

There is also a GitHub Actions workflow that runs it every day (needs SHEET_ID and GOOGLE_CREDENTIALS_JSON secrets).

Tests: `python -m pytest`
