from .models import *


class DocumentReader:
  """Base class: methods valid for every allowed format (TXT, MD, CSV).

  The specialized methods (normalize_text, create_excerpt, get_title, get_date)
  are defined in the subclasses TextReader and CSVReader.
  """

  # ---------- folder and file list ----------
  @staticmethod
  def choose_folder() -> Optional[Path]:
    """Asks the user for a folder; returns it, or None if it is not valid."""
    input_path = input("Which folder do you want to analyze? ")
    folder_path = Path.cwd() / input_path
    if not folder_path.is_dir():
      print("The given folder does not exist or is not valid.")
      return None
    return folder_path

  @staticmethod
  def open_document_list(folder_path: Optional[Path] = None) -> dict[int, Path]:
    """Recursively explores a directory (asked to the user if not given)."""
    if folder_path is None:
      folder_path = DocumentReader.choose_folder()
      if folder_path is None:
        return {}
    #Change(fix: session.json now lives in the analyzed folder, so it is not listed as a document)
    document_list = {
      number: path
      for number, path in enumerate(folder_path.rglob("*"), start=1)
      if path.is_file() and not path.is_symlink() and path.name != SESSION_FILE
    }
    skipped_links = sum(1 for path in folder_path.rglob("*") if path.is_symlink())
    if skipped_links:
      print(f"Symbolic links skipped: {skipped_links}")
    return document_list

  @staticmethod
  def allowed_extensions(document_list: dict[int, Path]) -> dict[int, tuple[str, str]]:
    """Keeps only the files with an allowed extension."""
    return {
      number: (path.name, path.suffix.lower())
      for number, path in document_list.items()
      if path.suffix.lower() in EXTENSIONS
    }

  @staticmethod
  def disallowed_extensions(document_list: dict[int, Path]) -> dict[int, tuple[str, str]]:
    """Returns the files excluded because of a disallowed extension."""
    return {
      number: (path.name, path.suffix.lower())
      for number, path in document_list.items()
      if path.suffix.lower() not in EXTENSIONS
    }

  @staticmethod
  def txt_documents(allowed_files: dict[int, tuple[str, str]]) -> dict[int, tuple[str, str]]:
    return {number: data for number, data in allowed_files.items() if data[1] == ".txt"}

  @staticmethod
  def csv_documents(allowed_files: dict[int, tuple[str, str]]) -> dict[int, tuple[str, str]]:
    return {number: data for number, data in allowed_files.items() if data[1] == ".csv"}

  @staticmethod
  def md_documents(allowed_files: dict[int, tuple[str, str]]) -> dict[int, tuple[str, str]]:
    return {number: data for number, data in allowed_files.items() if data[1] == ".md"}

  # ---------- common to all formats ----------
  @staticmethod
  def read_file(path: Path) -> tuple[str, str, bool]:
    """Reads a file safely. Returns (text, encoding used, is_binary)."""
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
      try:
        return data.decode("utf-16"), "utf-16", False
      except UnicodeDecodeError:
        pass
    if b"\x00" in data or CONTROL_BYTES_REGEX.search(data) is not None:
      return data.decode("latin-1"), "binary", True
    try:
      return data.decode("utf-8-sig"), "utf-8", False
    except UnicodeDecodeError:
      high_bytes = sum(1 for byte in data if byte >= 0x80)
      if high_bytes / len(data) > BINARY_HIGH_BYTES_RATIO:
        return data.decode("latin-1"), "binary", True
      return data.decode("cp1252", errors="replace"), "cp1252", False

  @staticmethod
  def count_words(text: str) -> int:
    return len(WORD_REGEX.findall(text))

  @staticmethod
  def tokenize(text: str) -> list[str]:
    return [token.lower() for token in WORD_REGEX.findall(text)]

  @staticmethod
  def unique_path(wanted: Path, current: Path) -> Path:
    """Returns 'wanted' if free (or the file itself), otherwise 'name (2)', 'name (3)', ..."""
    if not wanted.exists() or wanted.samefile(current):
      return wanted
    counter = 2
    while True:
      candidate = wanted.with_name(f"{wanted.stem} ({counter}){wanted.suffix}")
      if not candidate.exists():
        return candidate
      counter += 1

  @staticmethod
  def has_unreadable_chars(text: str) -> bool:
    distinct_chars = set(text.lower())
    return any(ch not in READABLE_CHARS and not ch.isspace() for ch in distinct_chars)

  @staticmethod
  def find_date(text: str) -> Optional[str]:
    """First valid date (ISO or European format) in the text, or None."""
    for pattern, order in DATE_PATTERNS:
      for match in pattern.finditer(text):
        parts = dict(zip(order, match.groups()))
        year, month, day = int(parts["year"]), int(parts["month"]), int(parts["day"])
        if not 1900 <= year <= 2100:
          continue
        try:
          datetime(year, month, day)
        except ValueError:
          continue
        if order[0] == "day" and day <= 12:
          return f"{year:04d}-{month:02d}-{day:02d} uncertain format"
        return f"{year:04d}-{month:02d}-{day:02d}"
    return None

  # ---------- specialized: defined in the subclasses ----------
  @staticmethod
  def normalize_text(text: str) -> str:
    raise NotImplementedError

  @staticmethod
  def create_excerpt(text: str) -> str:
    raise NotImplementedError

  @classmethod
  def get_title(cls, stem: str) -> str:
    raise NotImplementedError

  @classmethod
  def get_date(cls, text: str, stem: str) -> Optional[str]:
    raise NotImplementedError


class TextReader(DocumentReader):
  """Specialization for TXT and MD files."""

  @staticmethod
  def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = INVISIBLE_CHARS_REGEX.sub("", text)
    text = CONTROL_CHARS_REGEX.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [MULTIPLE_SPACES_REGEX.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = MULTIPLE_BLANK_LINES_REGEX.sub("\n\n", text)
    return text.strip()

  @staticmethod
  def create_excerpt(text: str, length: int = EXCERPT_LENGTH) -> str:
    flat = " ".join(text.split())
    if len(flat) <= length:
      excerpt = flat
    else:
      cut = flat[:length]
      last_space = cut.rfind(" ")
      if last_space > length // 2:
        cut = cut[:last_space]
      excerpt = cut + "..."
    if DocumentReader.has_unreadable_chars(text):
      excerpt = (excerpt + " " + UNREADABLE_CHARS_NOTE).strip()
    return excerpt

  @staticmethod
  def title_from_filename(stem: str) -> str:
    work = stem.replace("_", " ")
    protected_dates = []
    def keep_date(match):
      protected_dates.append(match.group(0))
      return f"\x00{len(protected_dates) - 1}\x00"
    for pattern, _order in DATE_PATTERNS:
      work = pattern.sub(keep_date, work)
    words = re.split(r"[_\-\s]+", work)
    title = " ".join(word.capitalize() for word in words if word)
    for index, date_text in enumerate(protected_dates):
      title = title.replace(f"\x00{index}\x00", date_text)
    return title if title else stem

  @classmethod
  def get_title(cls, stem: str) -> str:
    return cls.title_from_filename(stem)

  @classmethod
  def get_date(cls, text: str, stem: str) -> Optional[str]:
    """TXT/MD: the date is searched in the TEXT."""
    return cls.find_date(text)


class CSVReader(DocumentReader):
  """Specialization for CSV files."""

  @staticmethod
  def normalize_text(text: str) -> str:
    """Same rules as TextReader.normalize_text, but TABS ARE KEPT."""
    text = unicodedata.normalize("NFC", text)
    text = INVISIBLE_CHARS_REGEX.sub("", text)
    text = CONTROL_CHARS_REGEX.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r" {2,}", " ", line).strip(" ") for line in text.split("\n")]
    text = "\n".join(lines)
    text = MULTIPLE_BLANK_LINES_REGEX.sub("\n\n", text)
    return text.strip()

  @staticmethod
  def detect_delimiter(header_line: str) -> str:
    counts = {d: header_line.count(d) for d in CSV_DELIMITERS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","

  @staticmethod
  def looks_numeric(cell: str) -> bool:
    try:
      float(cell.strip().replace(".", "").replace(",", "."))
      return True
    except ValueError:
      return False

  @staticmethod
  def create_excerpt(text: str) -> str:
    """First data row in 'column: value' format, one pair per line."""
    first_line = text.strip().split("\n", 1)[0]
    if not first_line:
      return ""
    delimiter = CSVReader.detect_delimiter(first_line)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next((row for row in reader if row), [])
    first_row = next((row for row in reader if row), [])
    if header and all(CSVReader.looks_numeric(cell) for cell in header):
      first_row = header
      header = [f"col{index}" for index in range(1, len(header) + 1)]
    pairs = []
    for index, column in enumerate(header[:CSV_EXCERPT_MAX_COLUMNS]):
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
    if DocumentReader.has_unreadable_chars(text):
      excerpt += "\n" + UNREADABLE_CHARS_NOTE
    return excerpt

  @staticmethod
  def title_from_existing(stem: str) -> str:
    stem = unicodedata.normalize("NFC", stem)
    cleaned = re.sub(r"\s+", " ", stem).strip()
    return cleaned if cleaned else stem

  @staticmethod
  def date_from_title(stem: str) -> Optional[str]:
    return DocumentReader.find_date(stem.replace("_", " "))

  @classmethod
  def get_title(cls, stem: str) -> str:
    return cls.title_from_existing(stem)

  @classmethod
  def get_date(cls, text: str, stem: str) -> Optional[str]:
    """CSV: the date is searched ONLY in the file NAME."""
    return cls.date_from_title(stem)


# Reader to use for each extension
READERS = {".txt": TextReader, ".md": TextReader, ".csv": CSVReader}

# Compatibility: the existing loops that call FolderReader.xxx keep working
FolderReader = TextReader

#Change(one file per line: before, print(dict) wrote all the files on a single line - 145000 characters with 1000 files)
def print_file_list(files: dict) -> None:
  """Prints a file dictionary one entry per line, as '[number] name'.

  Works both for {number: Path} and for {number: (file_name, extension)}.

  Args:
      files (dict): The dictionary to print.
  """
  if not files:
    print("  (none)")
    return
  for number, item in files.items():
    name = item if isinstance(item, Path) else item[0]
    print(f"  [{number}] {name}")
  print(f"  total: {len(files)}")
