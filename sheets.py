import gspread

REVIEW_COLUMNS = {
    'id': 'Review ID',
    'product': 'Product',
    'date': 'Date',
    'rating': 'Rating',
    'text': 'Review',
    'scraped_at': 'First seen',
}

TESTIMONIAL_COLUMNS = {
    'id': 'ID',
    'rating': 'Rating',
    'text': 'Testimonial',
    'scraped_at': 'First seen',
}

RUN_COLUMNS = ['Run', 'Reviews found', 'New reviews', 'Testimonials found', 'New testimonials']


def open_sheet(credentials, sheet_id):
    # service account json from Google Cloud, the sheet has to be shared with its email
    client = gspread.service_account(filename=credentials)
    return client.open_by_key(sheet_id)


def get_worksheet(spreadsheet, title, header):
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(header))
        ws.append_row(header)
        ws.format('1:1', {'textFormat': {'bold': True}})
        ws.freeze(rows=1)
        return ws


def append_new(ws, rows, columns):
    """Adds only the rows whose id isn't in the sheet yet, so running it again doesn't make duplicates."""
    existing = set(ws.col_values(1)[1:])
    new = [row for row in rows if str(row['id']) not in existing]
    if new:
        # RAW (the default) so a review starting with "=" isn't turned into a formula
        ws.append_rows([[row[key] for key in columns] for row in new])
    return new


def write_table(ws, df):
    # summary is rewritten every run
    ws.clear()
    values = [list(df.columns)] + df.astype(object).where(df.notna(), '').values.tolist()
    ws.update(values, 'A1')
    ws.format('1:1', {'textFormat': {'bold': True}})
    ws.freeze(rows=1)


def update_sheet(spreadsheet, reviews, testimonials, summary):
    reviews_ws = get_worksheet(spreadsheet, 'Reviews', list(REVIEW_COLUMNS.values()))
    new_reviews = append_new(reviews_ws, reviews, REVIEW_COLUMNS)

    testimonials_ws = get_worksheet(spreadsheet, 'Testimonials', list(TESTIMONIAL_COLUMNS.values()))
    new_testimonials = append_new(testimonials_ws, testimonials, TESTIMONIAL_COLUMNS)

    summary_ws = get_worksheet(spreadsheet, 'Summary', list(summary.columns))
    write_table(summary_ws, summary)

    runs_ws = get_worksheet(spreadsheet, 'Runs', RUN_COLUMNS)
    run = reviews[0]['scraped_at'] if reviews else ''
    runs_ws.append_row([run, len(reviews), len(new_reviews), len(testimonials), len(new_testimonials)])

    return new_reviews, new_testimonials
