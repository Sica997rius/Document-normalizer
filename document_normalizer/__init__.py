"""document_normalizer: normalizes the TXT, MD and CSV files of a folder.

For each file the package cleans the text, proposes a tidy file name, finds
a date, builds a short excerpt and records everything in a JSON history.
Changes are written to disk only after one final confirmation.

Main pieces (one module each):
    config          fixed settings (extensions, regexes, notes, limits)
    models          Document and Session data classes
    folder_reader   folder scan, safe reading, TXT/MD rules  -> FolderReader
    csv_reader      CSV-only rules                            -> CSVReader
    session_store   reading/writing session.json
    cli             the interactive program (entry point: main)

Example, from Python:
    >>> from document_normalizer import FolderReader
    >>> FolderReader.title_from_filename("2024-03-15_meeting_notes")
    '2024-03-15 Meeting Notes'
"""

__version__ = "1.0.0"

from .csv_reader import CSVReader
from .folder_reader import FolderReader
from .models import Document, Session

__all__ = ["CSVReader", "Document", "FolderReader", "Session", "__version__"]
