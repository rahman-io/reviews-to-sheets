import subprocess
import sys
import threading
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
import fake_gspread
import fake_site
import report
import sheets
from scraper import parse_reviews, product_from_id, scrape_all


@pytest.fixture(scope='module')
def site():
    server = fake_site.start()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture(scope='module')
def scraped(site, browser):
    return scrape_all(browser, site)


def test_product_from_id():
    assert product_from_id('kids-light-up-sneakers-12') == 'Kids Light Up Sneakers'
    assert product_from_id('teal-potion-4') == 'Teal Potion'


def test_parse_reviews():
    html = '''<div id="latest-reviews"><div class="review" data-review-id="cat-ear-beanie-3" data-testid="review">
      <span data-testid="review-date">2022-10-05</span>
      <span data-testid="review-stars"><svg></svg><svg></svg><svg></svg></span>
      <p data-testid="review-text">Great beanie,
        but I wish there were more colors available.</p></div></div>'''
    assert parse_reviews(html) == [{
        'id': 'cat-ear-beanie-3', 'product': 'Cat Ear Beanie', 'date': '2022-10-05', 'rating': 3,
        'text': 'Great beanie, but I wish there were more colors available.',
    }]


def test_load_more(scraped):
    reviews, _ = scraped
    assert len(reviews) == 96  # 20 on the page + 4 clicks on Load More
    assert len({r['id'] for r in reviews}) == 96
    assert reviews[0]['id'] == 'teal-potion-4' and reviews[0]['date'] == '2023-05-18'
    assert reviews[-1]['id'] == 'women-sandals-1' and reviews[-1]['rating'] == 5
    assert sorted({r['rating'] for r in reviews}) == [2, 3, 4, 5]


def test_infinite_scroll(scraped):
    _, testimonials = scraped
    assert len(testimonials) == 60
    assert testimonials[0] == {'id': 'testimonial-0', 'rating': 5, 'scraped_at': testimonials[0]['scraped_at'],
                               'text': "We've been using this utility for years - awesome service!"}
    assert testimonials[-1]['id'] == 'testimonial-59'


def test_summary(scraped):
    reviews, _ = scraped
    df = report.summary(reviews)
    assert len(df) == 12
    assert df['Reviews'].sum() == 96
    sneakers = df[df['Product'] == 'Kids Light Up Sneakers'].iloc[0]
    assert sneakers['Reviews'] == 12 and sneakers['2 stars'] == 1
    assert sneakers['Lowest rated'].startswith('2/5: The sneakers are fun and eye-catching')
    assert list(df['Avg rating']) == sorted(df['Avg rating'], reverse=True)


def test_sheet_no_duplicates(scraped):
    reviews, testimonials = scraped
    book = fake_gspread.FakeSpreadsheet()
    summary = report.summary(reviews)

    new_reviews, new_testimonials = sheets.update_sheet(book, reviews, testimonials, summary)
    assert len(new_reviews) == 96 and len(new_testimonials) == 60
    assert list(book.sheets) == ['Reviews', 'Testimonials', 'Summary', 'Runs']
    assert book.sheets['Reviews'].rows[0] == ['Review ID', 'Product', 'Date', 'Rating', 'Review', 'First seen']
    assert book.sheets['Reviews'].frozen == 1

    # second run: a new review shows up at the top, the rest are already in the sheet
    new = dict(reviews[0], id='teal-potion-5', date='2023-05-20', text='Tastes like mint, nice.')
    new_reviews, new_testimonials = sheets.update_sheet(book, [new] + reviews, testimonials, summary)
    assert [r['id'] for r in new_reviews] == ['teal-potion-5'] and new_testimonials == []
    assert len(book.sheets['Reviews'].rows) == 98  # header + 97

    runs = book.sheets['Runs'].records()
    assert [r['New reviews'] for r in runs] == [96, 1]
    assert len(book.sheets['Summary'].rows) == 13  # rewritten, not appended


def test_main(site, tmp_path):
    # in a separate process because playwright is already running in this one (the browser fixture)
    code = f"""
import sys
sys.path[:0] = [{str(ROOT)!r}, {str(ROOT / 'tests')!r}]
import fake_gspread, main, sheets
book = fake_gspread.FakeSpreadsheet()
sheets.open_sheet = lambda credentials, sheet_id: book
sys.argv = ['main.py', '--url', {site!r}, '--out', {str(tmp_path)!r}, '--sheet-id', 'abc']
main.main()
print('rows:', {{name: len(ws.rows) for name, ws in book.sheets.items()}})
"""
    out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True).stdout
    print(out)
    assert '96 reviews (5 pages)' in out and '60 testimonials' in out
    assert 'Ratings: 5* 51, 4* 30, 3* 14, 2* 1, 1* 0' in out
    assert 'Google Sheet "Reviews tracker": 96 new reviews, 60 new testimonials' in out
    assert "rows: {'Reviews': 97, 'Testimonials': 61, 'Summary': 13, 'Runs': 2}" in out
    assert (tmp_path / 'reviews.csv').read_text(encoding='utf-8-sig').count('\n') == 97
    assert (tmp_path / 'testimonials.csv').exists() and (tmp_path / 'summary.csv').exists()


def test_error_screenshot(site, browser, tmp_path):
    fake_site.Handler.broken = True
    try:
        with pytest.raises(Exception):
            scrape_all(browser, site, out_dir=tmp_path, timeout=2000)
    finally:
        fake_site.Handler.broken = False
    assert (tmp_path / 'error.png').exists()
