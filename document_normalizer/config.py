"""Fixed settings shared by every module of the package.

Everything that you may want to tune (allowed extensions, excerpt length,
the list of "readable" characters, the notes written in the excerpt...)
lives here, so the rest of the code never contains "magic" values.

Nothing in this module does any work: it only defines constants.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Files that are processed
# ---------------------------------------------------------------------------

# Extensions that the program reads. The check ignores upper/lower case,
# so "REPORT.TXT" and "Data.Csv" are accepted too.
EXTENSIONS = [".txt", ".csv", ".md"]

# Name of the history file. It is created (or extended) in the folder the
# program is launched from, NOT inside the analyzed folder.
DEFAULT_SESSION_FILE = "session.json"

# Answers accepted as "yes" when the program asks to save the changes.
# Italian answers are accepted too, so a quick "s" is not read as "no".
YES_ANSWERS = ("y", "yes", "s", "si", "sì")

# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

# A "word" is a run of letters, digits or underscores (Unicode aware,
# so "città" counts as one word).
WORD_REGEX = re.compile(r"\w+", re.UNICODE)

# Horizontal whitespace: spaces, tabs and other blank characters that are
# not a line break. A run of them is collapsed into one single space.
MULTIPLE_SPACES_REGEX = re.compile(r"[ \t\r\f\v]+")

# Three or more line breaks in a row = more than one empty line.
# They are reduced to exactly one empty line.
MULTIPLE_BLANK_LINES_REGEX = re.compile(r"\n{3,}")

# Invisible characters that sneak in when text is copied from web pages or
# Word: zero-width space / non-joiner / joiner, the BOM and the soft hyphen.
# They are removed completely.
INVISIBLE_CHARS_REGEX = re.compile("[​‌‍﻿­]")

# Control characters (non printable). Tab (\x09), line feed (\x0a) and
# carriage return (\x0d) are NOT in the list: they are normal text.
CONTROL_CHARS_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Same list, but working on raw BYTES. It is used to recognize binary files
# before the content is decoded into text.
CONTROL_BYTES_REGEX = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# A file that is not valid UTF-8 and where more than this share of the bytes
# is "high" (>= 0x80) is treated as binary. Below the threshold it is treated
# as a Windows text file (cp1252), where only accented letters are high bytes.
BINARY_HIGH_BYTES_RATIO = 0.30

# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

# Each entry is (pattern, order of the captured groups).
#   1) ISO format:      2024-03-15
#   2) European format: 15/03/2024, 15.03.2024, 15-03-2024
# The order tells which group is the day, the month and the year.
DATE_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), ("year", "month", "day")),
    (re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b"), ("day", "month", "year")),
]

# Dates outside this range are ignored (they are usually not dates at all,
# for example codes or amounts that happen to look like a date).
MIN_YEAR = 1900
MAX_YEAR = 2100

# ---------------------------------------------------------------------------
# Excerpt
# ---------------------------------------------------------------------------

# Maximum length, in characters, of the excerpt of a text file and of each
# single value shown in the excerpt of a CSV file.
EXCERPT_LENGTH = 160

# Characters considered "readable". If a text contains anything else (apart
# from whitespace) a note is appended to its excerpt. The check ignores case,
# so only lowercase letters are listed.
READABLE_CHARS = set("qwertyuiopasdfghjklzxcvbnm,.-;:_òà\\1234567890'|!\"£$%&/()=?^@#é*[]èù+°ì")

# Excerpt used for binary files (their content is never shown).
BINARY_FILE_NOTE = "FILE BINARIO NON LEGIBILE."

# Note appended to the excerpt when unreadable / foreign characters are found.
UNREADABLE_CHARS_NOTE = "(alcuni caratteri non sono legibili o sono relativi ad altre lingue straniere)"

# ---------------------------------------------------------------------------
# CSV files
# ---------------------------------------------------------------------------

# Candidate column separators. The one that appears most often in the first
# line of the file is chosen; if none appears, the comma is used.
CSV_DELIMITERS = [",", ";", "\t", "|"]

# Maximum number of "column: value" lines shown in a CSV excerpt.
# Some files have hundreds of columns (MNIST has 785).
CSV_EXCERPT_MAX_COLUMNS = 20

# Largest field size accepted by the csv module. The default (131072
# characters) made files with a very long cell fail. 2**31 - 1 is the
# largest value accepted on every platform, 32-bit Windows included.
CSV_FIELD_SIZE_LIMIT = 2**31 - 1
