# document-normalizer

A command-line program that scans a folder (and all its subfolders),
normalizes **.TXT**, **.MD** and **.CSV** text files, and records every run
in a `session.json` file inside the analyzed folder. The `ricerca` command then
lets you search the processed documents in the session history.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Sica997rius/Document-normalizer/blob/main/document_normalizer_colab.ipynb)

## Try it in Google Colab

Open the notebook with the button above (or
[this link](https://colab.research.google.com/github/Sica997rius/Document-normalizer/blob/main/document_normalizer_colab.ipynb))
and choose *Runtime → Run all*. No GitHub account or installation is needed:
the package is embedded in the notebook, which also creates sample files to analyze.

To share it, send the link above. Everyone runs it in their own Colab session.

## What it does

1. Asks which folder to analyze (path relative to the folder the program is started from).
   `session.json` files are not listed as documents.
2. Lists every file found, one per line, and splits them into:
   - **allowed**: `.txt`, `.md`, `.csv`
   - **disallowed**: every other extension (only listed, never touched).
   Symbolic links are skipped.
3. For each allowed file:
   - **reads the file safely**: detects UTF-8 (with or without BOM), UTF-16 and cp1252;
     binary files (control bytes or too many "high" bytes) are detected and left unchanged;
   - **normalizes the text**: Unicode NFC form, invisible and control characters removed,
     line endings unified to `\n`, multiple spaces collapsed to one, at most one blank
     line in a row. In CSV files tabs are kept;
   - **computes the title**: for TXT/MD from the file name (underscores and hyphens become
     spaces, each word is capitalized, dates in the name are left as they are);
     for CSV files the name is only cleaned of extra spaces;
   - **counts the words** and creates an **excerpt** (160 characters for TXT/MD; for CSV
     files the first data row as `column: value`, up to 20 columns);
   - **looks for a date**: in the text for TXT/MD, only in the file name for CSV files.
     Recognized formats: `YYYY-MM-DD` and `DD/MM/YYYY` (also with `.` or `-`);
     a European date with day ≤ 12 is marked as `uncertain format`.
4. If the text or the title changed, rewrites the file as UTF-8 and/or renames it.
   If the new name is already taken it uses `name (2)`, `name (3)`, …
5. Appends the session (progressive ID, date, documents with original and new path,
   changes, date found, excerpt) to `session.json` **in the analyzed folder**.

### Save modes

At startup the program asks how to apply the changes:

| Choice | Behavior |
|---|---|
| `1` / `together` | applies all changes to all files right away, without asking |
| `2` / `separately` | asks `y/n` for each changed file before rewriting or renaming it |

Any other answer is rejected and the question is asked again.

> ⚠️ The program **modifies files on disk**. Make a copy of the folder before using it.

## Requirements

- Python **3.9** or later
- No external libraries: only the standard library is used
  (see [requirements.txt](requirements.txt))

## Installation

Get the code:

```bash
git clone https://github.com/Sica997rius/Document-normalizer.git
cd Document-normalizer
```

Installation needs **no internet connection**: the package is built by a small
backend in `_build/` that uses only the standard library, so pip does not have to
download setuptools.

From the project folder:

```bash
pip install .
```

or, in editable mode (code changes take effect without reinstalling):

```bash
pip install -r requirements.txt
```

Both create two commands: `document-normalizer` and `ricerca`.

A ready-made wheel is in `dist/`. Upload it to Google Colab and install it with:

```python
!pip install /content/document_normalizer-0.1.0-py3-none-any.whl
```

After changing the code, rebuild the wheel with:

```bash
pip wheel --no-deps . -w dist
```

## Usage

Normalization, from the terminal:

```bash
document-normalizer
```

or:

```bash
python -m document_normalizer
```

In a Colab cell:

```python
from document_normalizer import main
main()
```

Searching the history:

```bash
ricerca
```

or:

```bash
python -m ricerca
```

First type the analyzed folder (Enter = current folder), then one or more words: the documents containing **all** of them in the title,
file name, paths, changes or date are shown. Press Enter on an empty line to exit.

## The `session.json` file

Saved in the analyzed folder. A list of sessions, one per run on that folder:

```json
[
  {
    "session_id": 1,
    "session_date": "2026-10-17T10:30:00",
    "documents": {
      "folder/meeting_notes.txt": {
        "file_name": "meeting_notes.txt",
        "title": "Meeting Notes",
        "original_path": "folder/meeting_notes.txt",
        "new_path": "folder/Meeting Notes.txt",
        "changes": ["Changes made: title was changed, text was normalized"],
        "date": "2026-03-15",
        "excerpt": "Opening text of the document..."
      }
    }
  }
]
```

## Structure

```
document_normalizer/
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── README.md
├── document_normalizer_colab.ipynb   # Google Colab notebook
├── _build/
│   └── backend.py             # build backend, standard library only
├── dist/
│   └── document_normalizer-0.1.0-py3-none-any.whl
├── make_test_files.py         # random test-file generator
├── test_files/                # 18 sample files to try the program on
└── src/
    ├── document_normalizer/   # normalization
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── main.py
    │   ├── models.py
    │   └── readers.py
    └── ricerca/               # history search
        ├── __init__.py
        ├── __main__.py
        ├── main.py
        ├── models.py
        └── readers.py
```

| File | Contents |
|---|---|
| `models.py` | imports, constants (regexes, allowed extensions, excerpt length), `Session` and `Document` classes |
| `readers.py` | `DocumentReader` (base), `TextReader` (TXT/MD), `CSVReader` classes, `READERS` dictionary, `FolderReader` alias, `print_file_list` function |
| `document_normalizer/main.py` | the normalization program and the search functions |
| `ricerca/main.py` | `load_history`, `search_documents`, `print_results` and the `main()` search loop |

## Testing

`test_files/` holds 18 random sample files: TXT/MD/CSV in UTF-8, UTF-8 with BOM,
cp1252 and UTF-16, CRLF/CR line endings, an empty file, a binary file disguised
as text, disallowed extensions, subfolders and dates in the names.

The program **rewrites and renames** these files, so recreate them before every test:

```bash
python make_test_files.py test_files 18
```

The script takes `[folder] [count] [seed]`; the same seed always gives the same files.
For a larger test, e.g. 1000 files:

```bash
python make_test_files.py big_test 1000
```

Then start the program from the project folder and type `test_files` (or `big_test`)
as the folder to analyze.

## Compatibility notes

- Sessions saved by older versions use the `"Excerpt"` key; the search reads both
  `"excerpt"` and `"Excerpt"`.
- Older versions saved `session.json` in the folder the program was started from:
  to search it, type that folder (or press Enter from it) when `ricerca` asks.

## License

MIT - see [LICENSE](LICENSE).
