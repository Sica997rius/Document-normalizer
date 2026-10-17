from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from datetime import datetime
import json
import re
import unicodedata
import csv
import io

#==============FIXED_CONSTANTS================
WORD_REGEX = re.compile(r"\w+", re.UNICODE)
MULTIPLE_SPACES_REGEX = re.compile(r"[ \t\r\f\v]+")
MULTIPLE_BLANK_LINES_REGEX = re.compile(r"\n{3,}")
INVISIBLE_CHARS_REGEX = re.compile("[\u200b\u200c\u200d\ufeff\u00ad]")
CONTROL_CHARS_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

DATE_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), ("year", "month", "day")),
    (re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b"), ("day", "month", "year")),
]

EXCERPT_LENGTH = 160

READABLE_CHARS = set("qwertyuiopasdfghjklzxcvbnm,.-;:_òà\\1234567890'|!\"£$%&/()=?^@#é*[]èù+°ì")
BINARY_FILE_NOTE = "FILE BINARIO NON LEGIBILE."
UNREADABLE_CHARS_NOTE = "(alcuni caratteri non sono legibili o sono relativi ad altre lingue straniere)"

CSV_DELIMITERS = [",", ";", "\t", "|"]
CSV_EXCERPT_MAX_COLUMNS = 20

#Change(fix 2: the binary check now runs on the raw BYTES, before any decoding, so no byte can be silently dropped before the check)
CONTROL_BYTES_REGEX = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
#Change(fix 2: a file that is not valid UTF-8 and has more than 30% of "high" bytes (>= 0x80) is binary too - a 10-byte random file without control bytes was treated as text and rewritten)
BINARY_HIGH_BYTES_RATIO = 0.30
#Change(fix 4: the csv module refused fields longer than 131072 characters ("field larger than field limit"); 2**31-1 is the largest value accepted on every platform, 32-bit Windows included)
csv.field_size_limit(2**31 - 1)

#===================CLASSES===================
# File extensions supported for analysis
EXTENSIONS = [".txt", ".csv", ".md"]
CHARS_TO_EXCLUDE = [".", ",", "-", "_", "(", ")", "[", "]", "+", "?", "!"]
#Change(fix: the session history is saved in the analyzed folder, not in the folder the program is started from)
SESSION_FILE = "session.json"

@dataclass
class Session:
  """Represents an indexing session and keeps track of the history.

  This class maps the details of the documents processed in a specific
  run and dynamically computes the progressive ID by reading the
  'session.json' log file.

  Attributes:
      session_id (int): Unique identifier of the current session.
      session_date (datetime): Session start or end timestamp.
      documents (dict[str, Any]): Dictionary holding the metadata of the
          documents analyzed during the session.
      history_path (str): Path of the 'session.json' file to read.
  """
  session_id: int
  session_date: datetime
  documents: dict[str, Any] = field(default_factory=dict)
  history_path: str = SESSION_FILE

  @property
  def last_session_id(self) -> int:
    """Computes the highest ID stored in the session history.

    Safely reads the 'session.json' file if it exists, inspecting its
    format (list or single dictionary) to extract the highest ID.

    Returns:
        int: The highest numeric identifier found, or 0 if the file
            does not exist or is empty/corrupted.
    """
    try:
      with open(self.history_path, 'r', encoding="utf-8") as file:
        content = json.load(file)
        if isinstance(content, list):
          max_id = max((s.get('session_id', 0) for s in content), default=0)
        elif isinstance(content, dict):
          max_id = content.get('session_id', 0)
        else:
          max_id = 0
        return max_id
    except (FileNotFoundError, json.JSONDecodeError):
      return 0

@dataclass
class Document:
  """Data model for the structured handling of a single document.

  Collects all the information extracted from an analyzed file, including
  quantitative statistics, the normalized text and any changes.

  Attributes:
      document_id (str): Progressive or unique ID assigned to the document.
      title (str): Formatted or computed title of the document.
      original_title (str): Original file name on disk.
      word_count (int): Total word count after normalization.
      excerpt (str): Short textual preview of the content.
      content (str): The full, normalized text of the file.
      format (str): Extension of the original file (e.g. '.txt', '.md').
      path (str): Absolute or relative path of the file on disk.
      date (Optional[str]): Date possibly extracted from the text, in ISO format.
      extra (Optional[dict[str, Any]]): Optional additional metadata.
      original_content (Optional[str]): The raw text before normalization.
  """
  document_id: str
  title: str
  original_title: str
  word_count: int
  excerpt: str
  content: str
  format: str
  path: str
  date: Optional[str] = None
  extra: Optional[dict[str, Any]] = field(default_factory=dict)
  original_content: Optional[str] = None

  @property
  def title_changed(self) -> bool:
    """True if the computed title differs from the file name on disk (without extension)."""
    return self.title != Path(self.path).stem

  @property
  def text_changed(self) -> bool:
    """True if the normalized text differs from the raw text read from disk."""
    return self.original_content is not None and self.content != self.original_content

  @property
  def changes_made(self) -> str:
    """Checks whether the file changed compared to its original raw state.

    Compares the computed title with the original file name and checks
    whether the normalized text differs from the raw text.

    Returns:
        str: A descriptive string of the detected changes, or
            'No changes' if there are none.
    """
    changes = []
    if self.title_changed:
      changes.append("title was changed")
    if self.text_changed:
      changes.append("text was normalized")

    if changes:
      return "Changes made: " + ", ".join(changes)
    else:
      return "No changes"

  def indexed_document(self) -> dict[str, Any]:
    """Exports the document instance as a standard Python dictionary.

    Returns:
        dict[str, Any]: Dictionary representation of the dataclass fields.
    """
    return asdict(self)

  @classmethod
  def document_from_dict(cls, data: dict[str, Any]) -> "Document":
    """Initializes a document instance from a dictionary of data.

    Args:
        data (dict[str, Any]): Dictionary with the values to map onto the dataclass.

    Returns:
        Document: A new instance of the Document class.
    """
    return cls(**data)



# FolderReader class: set of methods used to read and normalize TXT and CSV files

