"""Folder scanning, safe file reading and normalization of TXT / MD files.

The FolderReader class groups static functions (no object needs to be
created): FolderReader.normalize_text(text), FolderReader.find_date(text)...

The CSV-specific rules are in csv_reader.py; the functions here that are
generic (reading a file, finding a date, checking readable characters) are
reused by the CSV reader too.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Optional, Union

from .config import (
    BINARY_HIGH_BYTES_RATIO,
    CONTROL_BYTES_REGEX,
    CONTROL_CHARS_REGEX,
    DATE_PATTERNS,
    EXCERPT_LENGTH,
    EXTENSIONS,
    INVISIBLE_CHARS_REGEX,
    MAX_YEAR,
    MIN_YEAR,
    MULTIPLE_BLANK_LINES_REGEX,
    MULTIPLE_SPACES_REGEX,
    READABLE_CHARS,
    UNREADABLE_CHARS_NOTE,
    WORD_REGEX,
)

# Type used by the file lists: {number: (file_name, lowercase_extension)}
FileTable = dict[int, tuple[str, str]]


class FolderReader:
    """Static utilities to explore a folder and to read and normalize text files."""

    # ------------------------------------------------------------------
    # Folder scanning
    # ------------------------------------------------------------------

    @staticmethod
    def open_document_list(folder: Optional[Union[str, Path]] = None) -> dict[int, Path]:
        """Lists every file of a folder and of all its subfolders.

        Args:
            folder: Folder to analyze, absolute or relative to the current
                directory. If omitted, the user is asked to type it.

        Returns:
            {progressive number: path}. The numbers are the ones printed in
            the lists and used as document IDs. An empty dict means the
            folder does not exist.
        """
        if folder is None:
            folder = input("Which folder do you want to analyze? ")
        # Path.cwd() / folder: a relative name is resolved from the current
        # directory; an absolute path simply replaces Path.cwd().
        folder_path = Path.cwd() / folder
        if not folder_path.is_dir():
            print("The given folder does not exist or is not valid.")
            return {}

        # rglob("*") walks the folder recursively. Folders are skipped
        # (is_file) and so are symbolic links: rewriting a link would modify
        # the file it points to, possibly outside the analyzed folder.
        document_list = {
            number: path
            for number, path in enumerate(folder_path.rglob("*"), start=1)
            if path.is_file() and not path.is_symlink()
        }
        skipped_links = sum(1 for path in folder_path.rglob("*") if path.is_symlink())
        if skipped_links:
            print(f"Symbolic links skipped: {skipped_links}")
        return document_list

    @staticmethod
    def allowed_extensions(document_list: dict[int, Path]) -> FileTable:
        """Keeps only the files whose extension is in EXTENSIONS.

        The extension is stored in lowercase, so "DATA.CSV" ends up in the
        CSV list together with "data.csv".
        """
        return {
            number: (path.name, path.suffix.lower())
            for number, path in document_list.items()
            if path.suffix.lower() in EXTENSIONS
        }

    @staticmethod
    def disallowed_extensions(document_list: dict[int, Path]) -> FileTable:
        """The opposite of allowed_extensions: files that will be ignored."""
        return {
            number: (path.name, path.suffix.lower())
            for number, path in document_list.items()
            if path.suffix.lower() not in EXTENSIONS
        }

    @staticmethod
    def txt_documents(allowed_files: FileTable) -> FileTable:
        """Only the ".txt" files of the allowed list."""
        return {number: data for number, data in allowed_files.items() if data[1] == ".txt"}

    @staticmethod
    def csv_documents(allowed_files: FileTable) -> FileTable:
        """Only the ".csv" files of the allowed list."""
        return {number: data for number, data in allowed_files.items() if data[1] == ".csv"}

    @staticmethod
    def md_documents(allowed_files: FileTable) -> FileTable:
        """Only the ".md" files of the allowed list."""
        return {number: data for number, data in allowed_files.items() if data[1] == ".md"}

    # ------------------------------------------------------------------
    # Safe reading
    # ------------------------------------------------------------------

    @staticmethod
    def read_file(path: Path) -> tuple[str, str, bool]:
        """Reads a file without ever losing a byte, and tells how it was decoded.

        Why this exists: opening a file with open(..., errors="ignore")
        silently throws away every byte that is not valid UTF-8. A Windows
        file lost its accents when rewritten, and a small binary file could
        pass the binary check because its "strange" bytes had already been
        dropped. Here the file is read as raw bytes and decoded step by step.

        Order of the checks:
          1. Starts with a UTF-16 BOM       -> UTF-16 text (it contains NUL
             bytes, so it must be checked before the binary test).
          2. Contains NUL / control bytes   -> binary.
          3. Valid UTF-8 (BOM removed)      -> UTF-8 text.
          4. Not valid UTF-8:
               more than BINARY_HIGH_BYTES_RATIO high bytes -> binary,
               otherwise -> Windows text (cp1252), accents preserved.

        Binary content is decoded as latin-1, which maps every byte to one
        character 1:1, so nothing is lost (the program never rewrites a
        binary file anyway).

        Args:
            path: The file to read.

        Returns:
            (text, encoding name, is_binary). The encoding is one of
            "utf-8", "utf-16", "cp1252", "binary".
        """
        data = path.read_bytes()
        if data.startswith((b"\xff\xfe", b"\xfe\xff")):
            try:
                return data.decode("utf-16"), "utf-16", False
            except UnicodeDecodeError:
                pass  # looked like UTF-16 but is not: continue with the other checks
        if b"\x00" in data or CONTROL_BYTES_REGEX.search(data) is not None:
            return data.decode("latin-1"), "binary", True
        try:
            # "utf-8-sig" also removes the UTF-8 BOM if present.
            return data.decode("utf-8-sig"), "utf-8", False
        except UnicodeDecodeError:
            high_bytes = sum(1 for byte in data if byte >= 0x80)
            if high_bytes / len(data) > BINARY_HIGH_BYTES_RATIO:
                return data.decode("latin-1"), "binary", True
            return data.decode("cp1252", errors="replace"), "cp1252", False

    @staticmethod
    def unique_path(wanted: Path, current: Path) -> Path:
        """Finds a free name for a rename.

        Returns "wanted" if no other file has that name. If the name is
        taken, returns "name (2).ext", "name (3).ext", ... in the same folder.

        "wanted" is also accepted when it IS the current file: on Windows
        "DATA.CSV" and "Data.csv" are the same file, and a case-only rename
        must be allowed.

        Args:
            wanted: The desired new path.
            current: The file that is being renamed.
        """
        if not wanted.exists() or wanted.samefile(current):
            return wanted
        counter = 2
        while True:
            candidate = wanted.with_name(f"{wanted.stem} ({counter}){wanted.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    # ------------------------------------------------------------------
    # Normalization and analysis of TXT / MD text
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_text(text: str) -> str:
        """Cleans a text. Steps, in this order:

        1. Unicode NFC: "e" + combining accent becomes the single letter "é",
           so identical words are also identical in the computer's memory.
        2. Invisible characters (zero-width, BOM, soft hyphen) removed.
        3. Control characters replaced by a space.
        4. Windows (\\r\\n) and old Mac (\\r) line endings become \\n.
        5. On every line, runs of spaces/tabs become one space, and spaces at
           the start and end of the line are removed.
        6. More than one empty line in a row becomes a single empty line.
        7. Blank space at the start and end of the whole text removed.

        Note: step 7 also removes the final line break that most files have,
        so almost every file is reported as "text was normalized".
        """
        text = unicodedata.normalize("NFC", text)
        text = INVISIBLE_CHARS_REGEX.sub("", text)
        text = CONTROL_CHARS_REGEX.sub(" ", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [MULTIPLE_SPACES_REGEX.sub(" ", line).strip() for line in text.split("\n")]
        text = "\n".join(lines)
        text = MULTIPLE_BLANK_LINES_REGEX.sub("\n\n", text)
        return text.strip()

    @staticmethod
    def count_words(text: str) -> int:
        """Number of words (runs of letters, digits and underscores)."""
        return len(WORD_REGEX.findall(text))

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """The words of the text, in lowercase (not used by the program yet;
        useful for a future search index)."""
        return [token.lower() for token in WORD_REGEX.findall(text)]

    @staticmethod
    def has_unreadable_chars(text: str) -> bool:
        """True if the text contains characters outside READABLE_CHARS.

        Upper/lower case is ignored and whitespace is always allowed.
        The distinct characters are collected first with set(): on a big file
        this checks a few dozen characters instead of millions.
        """
        distinct_chars = set(text.lower())
        return any(ch not in READABLE_CHARS and not ch.isspace() for ch in distinct_chars)

    @staticmethod
    def create_excerpt(text: str, length: int = EXCERPT_LENGTH) -> str:
        """Short preview of a TXT / MD text.

        The text is flattened on one line; if it is longer than "length" it is
        cut at the last space (so no word is cut in half) and "..." is added.
        If the WHOLE text contains unreadable characters, UNREADABLE_CHARS_NOTE
        is appended.

        Args:
            text: The normalized text.
            length: Maximum number of characters before the note.
        """
        flat = " ".join(text.split())
        if len(flat) <= length:
            excerpt = flat
        else:
            cut = flat[:length]
            last_space = cut.rfind(" ")
            # Cut at the last space only if it is not too far back
            # (a very long first word would otherwise leave almost nothing).
            if last_space > length // 2:
                cut = cut[:last_space]
            excerpt = cut + "..."
        if FolderReader.has_unreadable_chars(text):
            excerpt = (excerpt + " " + UNREADABLE_CHARS_NOTE).strip()
        return excerpt

    @staticmethod
    def find_date(text: str) -> Optional[str]:
        """Finds the first real date in the text and returns it as "YYYY-MM-DD".

        A match is accepted only if:
          - the year is between MIN_YEAR and MAX_YEAR;
          - the date exists in the calendar (31/02/2024 is skipped).

        A European date whose day is 12 or less (e.g. 05/06/2024) could also
        be read as month/day (American style): it is returned with the
        suffix " uncertain format". ISO dates are never ambiguous.

        Args:
            text: Where to search.

        Returns:
            The date, possibly with " uncertain format", or None.
        """
        # Imported here to keep the module header short; datetime is only
        # needed to validate the calendar date.
        from datetime import datetime

        for pattern, order in DATE_PATTERNS:
            for match in pattern.finditer(text):
                parts = dict(zip(order, match.groups()))
                year, month, day = int(parts["year"]), int(parts["month"]), int(parts["day"])
                if not MIN_YEAR <= year <= MAX_YEAR:
                    continue
                try:
                    datetime(year, month, day)  # raises ValueError for impossible dates
                except ValueError:
                    continue
                if order[0] == "day" and day <= 12:
                    return f"{year:04d}-{month:02d}-{day:02d} uncertain format"
                return f"{year:04d}-{month:02d}-{day:02d}"
        return None

    @staticmethod
    def title_from_filename(stem: str) -> str:
        """Builds a readable title from a file name (without extension).

        Underscores and hyphens become spaces and every word gets a capital
        first letter: "my_important-notes" -> "My Important Notes".

        Dates inside the name are kept whole: "2024-03-15_minutes" becomes
        "2024-03-15 Minutes", not "2024 03 15 Minutes". To do that each date
        is replaced by a placeholder (\\x00 + number + \\x00, characters that
        cannot appear in a file name), the words are processed, then the
        dates are put back.

        A name made only of underscores/hyphens would give an empty title
        (and the file would be renamed to just ".txt", a hidden file): in
        that case the original name is returned.
        """
        # Underscores first become spaces so that the date patterns, which
        # need a word boundary, can see a date next to an underscore.
        work = stem.replace("_", " ")
        protected_dates: list[str] = []

        def keep_date(match: re.Match) -> str:
            """Stores the matched date and returns its placeholder."""
            protected_dates.append(match.group(0))
            return f"\x00{len(protected_dates) - 1}\x00"

        for pattern, _order in DATE_PATTERNS:
            work = pattern.sub(keep_date, work)
        words = re.split(r"[_\-\s]+", work)
        title = " ".join(word.capitalize() for word in words if word)
        for index, date_text in enumerate(protected_dates):
            title = title.replace(f"\x00{index}\x00", date_text)
        return title if title else stem
