# A small local copy of the two pages with the same html and the same loading behaviour:
# /reviews loads 20 reviews at a time with javascript and a Load More button,
# /testimonials loads the next 10 when the last one is scrolled into view (like htmx "revealed").
# The data is what the real pages had when this was written.

import html
import http.server
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DATA = Path(__file__).parent / 'data'
REVIEWS = [dict(zip(['rid', 'date', 'rating', 'text'], r)) for r in json.loads((DATA / 'reviews.json').read_text())]
TESTIMONIALS = json.loads((DATA / 'testimonials.json').read_text())

STAR = '<svg width="20px" height="20px" viewBox="0 0 64 64" role="img"><path d="M62 25.2H39.1L32 3z" fill="#ffce31"></path></svg>'

REVIEWS_PAGE = """<!doctype html><html><head><title>reviews</title></head><body>
<h1>Latest reviews</h1>
<div id="latest-reviews" data-last-cursor=""></div>
<div class="spinner-border d-none" role="status" id="page-spinner"></div>
<button id="page-load-more" class="d-block btn btn-primary" onclick="loadPage(20)">Load More</button>
<style>.d-none { display: none !important; }</style>
<script>
const STAR = '%s';
async function loadPage(first) {
  const root = document.getElementById('latest-reviews');
  const spinner = document.getElementById('page-spinner');
  const loadMore = document.getElementById('page-load-more');
  spinner.classList.remove('d-none');
  loadMore.classList.add('d-none');
  const response = await fetch('/api/reviews?first=' + first + '&after=' + root.dataset.lastCursor);
  const data = await response.json();
  for (const review of data.reviews) {
    const div = document.createElement('div');
    div.className = 'review';
    div.dataset.reviewId = review.rid;
    div.dataset.testid = 'review';
    div.innerHTML = '<span data-testid="review-date"></span><span data-testid="review-stars">' + STAR.repeat(review.rating) +
      '</span><p data-testid="review-text"></p>';
    div.querySelector('[data-testid=review-date]').textContent = review.date;
    div.querySelector('[data-testid=review-text]').textContent = review.text;
    root.appendChild(div);
    root.dataset.lastCursor = data.cursor;
  }
  spinner.classList.add('d-none');
  if (data.hasNextPage) loadMore.classList.remove('d-none');
}
document.addEventListener('DOMContentLoaded', () => loadPage(20));
</script></body></html>""" % STAR

TESTIMONIALS_PAGE = """<!doctype html><html><head><title>testimonials</title>
<style>.testimonial { height: 150px; border-bottom: 1px solid #ddd; }</style></head><body>
<h1>Testimonials</h1>
<div class="testimonials">%s</div>
<script>
const observer = new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (!entry.isIntersecting) continue;
    const el = entry.target;
    const next = el.dataset.next;
    observer.unobserve(el);
    delete el.dataset.next;
    fetch(next).then(r => r.text()).then(html => {
      el.insertAdjacentHTML('afterend', html);
      watch();
    });
  }
});
function watch() { document.querySelectorAll('.testimonial[data-next]').forEach(el => observer.observe(el)); }
watch();
</script></body></html>"""


def testimonials_html(page):
    start = (page - 1) * 10
    items = TESTIMONIALS[start:start + 10]
    out = []
    for i, (rating, text) in enumerate(items, start=start):
        last = i == start + len(items) - 1 and start + 10 < len(TESTIMONIALS)
        next_page = f' data-next="/api/testimonials?page={page + 1}"' if last else ''
        out.append(f'<div class="testimonial"{next_page}><identicon-svg username="testimonial-{i}"></identicon-svg>'
                    f'<div><span class="rating">{STAR * rating}</span><p class="text">{html.escape(text)}</p></div></div>')
    return '\n'.join(out)


class Handler(http.server.BaseHTTPRequestHandler):
    reviews = REVIEWS
    broken = False  # True = the page has no reviews, like when the layout changed

    def send(self, body, content_type='text/html'):
        self.send_response(200)
        self.send_header('Content-Type', f'{content_type}; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == '/reviews':
            self.send('<html><body><h1>Down for maintenance</h1></body></html>' if self.broken else REVIEWS_PAGE)
        elif url.path == '/api/reviews':
            time.sleep(0.2)  # a bit of latency, like a real api
            first = int(query['first'][0])
            after = int(query.get('after', ['0'])[0] or 0)
            items = self.reviews[after:after + first]
            self.send(json.dumps({'reviews': items, 'cursor': after + len(items),
                                  'hasNextPage': after + first < len(self.reviews)}), 'application/json')
        elif url.path == '/testimonials':
            self.send(TESTIMONIALS_PAGE % testimonials_html(1))
        elif url.path == '/api/testimonials':
            time.sleep(0.2)
            self.send(testimonials_html(int(query['page'][0])))
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass


def start():
    return http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
