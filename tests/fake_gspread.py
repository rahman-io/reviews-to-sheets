# Just enough of gspread to test the sheet code without a Google account.
import json

import gspread


class FakeWorksheet:
    def __init__(self, title):
        self.title = title
        self.rows = []
        self.frozen = 0
        self.bold = False

    def append_row(self, values, **kwargs):
        self.append_rows([values])

    def append_rows(self, values, **kwargs):
        json.dumps(values)  # the real api sends json, numpy numbers would fail here
        self.rows.extend([list(v) for v in values])

    def col_values(self, col):
        return [str(row[col - 1]) for row in self.rows if len(row) >= col]

    def clear(self):
        self.rows = []

    def update(self, values, range_name=None, **kwargs):
        json.dumps(values)
        self.rows = [list(v) for v in values]

    def format(self, ranges, fmt):
        self.bold = fmt.get('textFormat', {}).get('bold', False)

    def freeze(self, rows=None, cols=None):
        self.frozen = rows

    def records(self):
        header, *rows = self.rows
        return [dict(zip(header, row)) for row in rows]


class FakeSpreadsheet:
    title = 'Reviews tracker'

    def __init__(self):
        self.sheets = {}

    def worksheet(self, title):
        if title not in self.sheets:
            raise gspread.WorksheetNotFound(title)
        return self.sheets[title]

    def add_worksheet(self, title, rows, cols, index=None):
        self.sheets[title] = FakeWorksheet(title)
        return self.sheets[title]
