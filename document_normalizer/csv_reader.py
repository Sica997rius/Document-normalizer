"""Rules that apply only to CSV files.

CSV files differ from TXT / MD files in four points:
  1. Normalization keeps TABS: in a tab-separated file they are the column
     separator, and collapsing them would merge the columns.
  2. The title is the EXISTING file name, only cleaned (no capital letters
     added, underscores kept): data files often have names that other
     programs expect.
  3. The date is searched ONLY in the file name, never in the content
     (a data file is full of numbers that may look like dates).
  4. The excerpt is the first data row, as one "column: value" line per column.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from typing import Optional

from .config import (
    CONTROL_CHARS_REGEX,
    CSV_DELIMITERS,
    CSV_EXCERPT_MAX_COLUMNS,
    CSV_FIELD_SIZE_LIMIT,
    EXCERPT_LENGTH,
    INVISIBLE_CHARS_REGEX,
    MULTIPLE_BLANK_LINES_REGEX,
    UNREADABLE_CHARS_NOTE,
)
from .folder_reader import FolderReader

# Raise the csv module's limit once, when the module is imported: by default
# a single cell longer than 131072 characters raises "field larger than
# field limit" and the file could not be processed.
csv.field_size_limit(CSV_FIELD_SIZE_LIMIT)


class CSVReader:
    """Static utilities valid only for CSV documents."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Same cleaning as FolderReader.normalize_text, but TABS ARE KEPT.

        Only runs of two or more SPACES are collapsed, and only spaces are
        removed at the start and end of each line.
        """
        text = unicodedata.normalize("NFC", text)
        text = INVISIBLE_CHARS_REGEX.sub("", text)
        text = CONTROL_CHARS_REGEX.sub(" ", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r" {2,}", " ", line).strip(" ") for line in text.split("\n")]
        text = "\n".join(lines)
        text = MULTIPLE_BLANK_LINES_REGEX.sub("\n\n", text)
        return text.strip()

    @staticmethod
    def title_from_existing(stem: str) -> str:
        """Keeps the existing file name, only cleaned.

        Unicode NFC, runs of blanks collapsed into one space, blanks at the
        ends removed: "sales  2024 " -> "sales 2024". An empty result gives
        back the original name (never an empty title).
        """
        stem = unicodedata.normalize("NFC", stem)
        cleaned = re.sub(r"\s+", " ", stem).strip()
        return cleaned if cleaned else stem

    @staticmethod
    def date_from_title(stem: str) -> Optional[str]:
        """Searches a date ONLY in the file name.

        Underscores are turned into spaces first: the date patterns need a
        word boundary, and for regular expressions "_" is part of a word,
        so "sales_2024-03-15" would not match otherwise.
        """
        return FolderReader.find_date(stem.replace("_", " "))

    @staticmethod
    def detect_delimiter(header_line: str) -> str:
        """Picks the separator that appears most often in the first line.

        Example: "cliente;città;importo" -> ";" (2 times, the comma 0 times).
        If no candidate appears (a single-column file), the comma is used.
        """
        counts = {delimiter: header_line.count(delimiter) for delimiter in CSV_DELIMITERS}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","

    @staticmethod
    def looks_numeric(cell: str) -> bool:
        """True if the cell is a number, Italian format included ("1.250,50").

        Used to recognize files without a header row: if every cell of the
        first row is a number, that row is data, not column names.
        """
        try:
            float(cell.strip().replace(".", "").replace(",", "."))
            return True
        except ValueError:
            return False

    @staticmethod
    def create_excerpt(text: str) -> str:
        """First data row as "column: value" lines, one per column.

        Example:
            cliente;città;importo        cliente: Rossi
            Rossi;Torino;1.250,50   ->   città: Torino
                                         importo: 1.250,50

        Details:
          - The whole text is given to the csv module through io.StringIO
            (which makes a string behave like an open file). This way a
            quoted value that contains a line break is read completely.
          - If the first row is made only of numbers, the file has no header:
            the columns are named col1, col2, ... and that row is the values.
          - A value or column name longer than EXCERPT_LENGTH is shortened,
            and a value spanning several lines is shown on one line.
          - At most CSV_EXCERPT_MAX_COLUMNS columns are shown; the rest is
            summarized as "... (+N more columns)".
          - UNREADABLE_CHARS_NOTE is added on its own line when needed.
        """
        first_line = text.strip().split("\n", 1)[0]
        if not first_line:
            return ""
        delimiter = CSVReader.detect_delimiter(first_line)
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        # "if row" skips empty lines before the header or between rows.
        header = next((row for row in reader if row), [])
        first_row = next((row for row in reader if row), [])
        if header and all(CSVReader.looks_numeric(cell) for cell in header):
            first_row = header
            header = [f"col{index}" for index in range(1, len(header) + 1)]

        pairs = []
        for index, column in enumerate(header[:CSV_EXCERPT_MAX_COLUMNS]):
            # A short row (fewer cells than the header) gives empty values.
            value = first_row[index] if index < len(first_row) else ""
            value = " ".join(value.split())
            if len(value) > EXCERPT_LENGTH:
                value = value[:EXCERPT_LENGTH] + "..."
            column = " ".join(column.split())
            if len(column) > EXCERPT_LENGTH:
                column = column[:EXCERPT_LENGTH] + "..."
            pairs.append(f"{column}: {value}")
        if len(header) > CSV_EXCERPT_MAX_COLUMNS:
            pairs.append(f"... (+{len(header) - CSV_EXCERPT_MAX_COLUMNS} more columns)")

        excerpt = "\n".join(pairs)
        if FolderReader.has_unreadable_chars(text):
            excerpt += "\n" + UNREADABLE_CHARS_NOTE
        return excerpt
