import argparse
import os
from collections import Counter
from pathlib import Path

from playwright.sync_api import sync_playwright

import report
from scraper import BASE_URL, scrape_all


def main():
    parser = argparse.ArgumentParser(description='Scrape product reviews and testimonials into Google Sheets')
    parser.add_argument('--sheet-id', default=os.environ.get('SHEET_ID'),
                        help='the long id in the sheet url, between /d/ and /edit')
    parser.add_argument('--credentials', default=os.environ.get('GOOGLE_CREDENTIALS', 'credentials.json'),
                        help='service account json file (default credentials.json)')
    parser.add_argument('--no-sheets', action='store_true', help='only save the csv files')
    parser.add_argument('--headed', action='store_true', help='show the browser window')
    parser.add_argument('--url', default=BASE_URL)
    parser.add_argument('--out', default='output')
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        try:
            reviews, testimonials = scrape_all(browser, args.url, out_dir)
        finally:
            browser.close()

    ratings = Counter(r['rating'] for r in reviews)
    print('Ratings: ' + ', '.join(f'{stars}* {ratings[stars]}' for stars in range(5, 0, -1)))

    summary = report.summary(reviews)
    report.save_csv(out_dir, reviews, testimonials, summary)
    print(f'Saved reviews.csv, testimonials.csv and summary.csv to {out_dir}/')

    if args.no_sheets:
        return
    if not args.sheet_id:
        print('No --sheet-id given, skipped Google Sheets (use --no-sheets to hide this)')
        return

    import sheets  # only needed here, so --no-sheets works without the google setup
    spreadsheet = sheets.open_sheet(args.credentials, args.sheet_id)
    new_reviews, new_testimonials = sheets.update_sheet(spreadsheet, reviews, testimonials, summary)
    print(f'Google Sheet "{spreadsheet.title}": {len(new_reviews)} new reviews, {len(new_testimonials)} new testimonials')


if __name__ == '__main__':
    main()
