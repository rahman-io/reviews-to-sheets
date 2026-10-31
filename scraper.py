import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeout

BASE_URL = 'https://web-scraping.dev'


def block_extras(route):
    # images and fonts are not needed for the data and make the pages slower
    if route.request.resource_type in ('image', 'font', 'media'):
        route.abort()
    else:
        route.continue_()


def product_from_id(review_id):
    # "kids-light-up-sneakers-12" -> "Kids Light Up Sneakers"
    slug = re.sub(r'-\d+$', '', review_id)
    return slug.replace('-', ' ').title()


def count_stars(element):
    return len(element.find_all('svg')) if element else None


def clean(text):
    return ' '.join(text.split())


def parse_reviews(html):
    soup = BeautifulSoup(html, 'html.parser')
    reviews = []
    for div in soup.select('#latest-reviews [data-testid=review]'):
        review_id = div['data-review-id']
        reviews.append({
            'id': review_id,
            'product': product_from_id(review_id),
            'date': div.select_one('[data-testid=review-date]').text.strip(),
            'rating': count_stars(div.select_one('[data-testid=review-stars]')),
            'text': clean(div.select_one('[data-testid=review-text]').text),
        })
    return reviews


def parse_testimonials(html):
    soup = BeautifulSoup(html, 'html.parser')
    testimonials = []
    for div in soup.select('.testimonial'):
        user = div.select_one('identicon-svg')
        testimonials.append({
            'id': user['username'] if user else None,
            'rating': count_stars(div.select_one('.rating')),
            'text': clean(div.select_one('.text').text),
        })
    return testimonials


def scrape_reviews(page, base_url=BASE_URL):
    """The reviews come from a GraphQL api, 20 at a time, with a Load More button."""
    page.goto(f'{base_url}/reviews')
    page.wait_for_selector('[data-testid=review]')

    pages = 1
    cards = page.locator('[data-testid=review]')
    button = page.locator('#page-load-more')
    # the button is hidden while loading and stays hidden after the last page
    while button.is_visible():
        count = cards.count()
        button.click()
        page.wait_for_function('n => document.querySelectorAll("[data-testid=review]").length > n', arg=count)
        pages += 1
    reviews = parse_reviews(page.content())
    print(f'{len(reviews)} reviews ({pages} pages)')
    return reviews


def scrape_testimonials(page, base_url=BASE_URL, wait=5000):
    """Infinite scroll: the next 10 load when the last testimonial comes into view."""
    page.goto(f'{base_url}/testimonials')
    page.wait_for_selector('.testimonial')

    cards = page.locator('.testimonial')
    while True:
        count = cards.count()
        cards.last.scroll_into_view_if_needed()
        try:
            page.wait_for_function('n => document.querySelectorAll(".testimonial").length > n', arg=count, timeout=wait)
        except PlaywrightTimeout:
            break  # nothing new came in, so this was the end
    testimonials = parse_testimonials(page.content())
    print(f'{len(testimonials)} testimonials')
    return testimonials


def scrape_all(browser, base_url=BASE_URL, out_dir=None, timeout=30000):
    context = browser.new_context(viewport={'width': 1280, 'height': 900})
    context.set_default_timeout(timeout)
    page = context.new_page()
    page.route('**/*', block_extras)
    try:
        reviews = scrape_reviews(page, base_url)
        testimonials = scrape_testimonials(page, base_url)
    except Exception:
        # a screenshot makes it much easier to see what went wrong (layout change, blocked, ...)
        if out_dir:
            page.screenshot(path=str(out_dir / 'error.png'), full_page=True)
            print(f'Saved a screenshot to {out_dir / "error.png"}')
        raise
    finally:
        context.close()

    scraped_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    for row in reviews + testimonials:
        row['scraped_at'] = scraped_at
    return reviews, testimonials
