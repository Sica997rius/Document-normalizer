# document-normalizer

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Sica997rius/Document-normalizer/blob/main/document_normalizer_colab.ipynb)

A command-line program that scans a folder (and all its subfolders), cleans up
the **.TXT**, **.MD** and **.CSV** files, gives them a tidy name, finds a date,
builds a short excerpt of each file and records every run in a `session.json`
file inside the analyzed folder. A second program, `ricerca`, searches that history.

Written in Python with the **standard library only**: no packages to install
(see [requirements.txt](requirements.txt)).

## Try it in Google Colab

Open the notebook with the button above (or
[this link](https://colab.research.google.com/github/Sica997rius/Document-normalizer/blob/main/document_normalizer_colab.ipynb))
and choose *Runtime → Run all*, then answer the questions of the program.
No installation and no GitHub account are needed: the notebook downloads this
repository, copies the 18 sample files of `test_files/` and runs the code of `src/`.
You can also upload your own files.

To share it, just send the link: everyone runs it in their own Colab session.

## What it does

For every file in the folder and its subfolders:

| | `.txt` and `.md` files | `.csv` files |
|---|---|---|
| **Text cleanup** | double spaces and tabs, extra blank lines, Windows line endings, invisible characters | the same, but **tabs are kept** (they separate the columns) |
| **New name** | capital letters and spaces: `meeting_notes.txt` → `Meeting Notes.txt` | the name is only cleaned: `report  month.csv` → `report month.csv` |
| **Date** | the first valid date **in the text** | only if it is **in the file name** |
| **Excerpt** | the first 160 characters | the first data row, one `column: value` pair per line |

Other rules:

- **Encodings**: UTF-8 (with or without BOM), UTF-16 and Windows cp1252 are read
  correctly; rewritten files are saved as UTF-8.
- **Binary files** saved with a `.txt`/`.csv` extension: excerpt
  `FILE BINARIO NON LEGIBILE.`, the content is never modified.
- **Foreign or unexpected characters**: the excerpt gets the note
  `(alcuni caratteri non sono legibili o sono relativi ad altre lingue straniere)`.
- **Dates**: `2024-03-15`, `15/03/2024`, `15.03.2024`, `15-03-2024`; impossible dates
  (`31/02/2024`) are skipped; dates that could be read both ways (`05/06/2024`) are
  marked `uncertain format`.
- **Name already taken**: `Name (2).txt`, `Name (3).txt`, …
- **Empty files** are skipped, **symbolic links** ignored, **other extensions**
  listed but never touched, `session.json` files are not listed.

### Save modes

After listing the files the program asks how to apply the changes:

| Answer | Behavior |
|---|---|
| `1` / `together` | applies all changes to all files, without asking |
| `2` / `separately` | asks `y/n` for each changed file before rewriting or renaming it |

Any other answer is rejected and the question is asked again.

> ⚠️ The program **rewrites and renames files on disk**. Work on a copy of your folder.

## Run it on your computer

Requirements: **Python 3.9** or later. No packages to install.

```bash
git clone https://github.com/Sica997rius/Document-normalizer.git
cd Document-normalizer
```

Start the normalization from the `src` folder:

```bash
cd src
python -m document_normalizer
```

When it asks for the folder, type its path **relative to `src`**: for the 18 sample
files, `../test_files`.

Search the history (from the `src` folder too):

```bash
python -m ricerca
```

Type the same folder, then one or more words: the documents containing **all** of
them in the title, file name, paths, changes, date or excerpt are shown.
Press Enter on an empty line to exit.

## Sample files

`test_files/` holds 18 random files that cover every case: TXT/MD/CSV in UTF-8,
UTF-8 with BOM, cp1252 and UTF-16, CRLF/CR line endings, an empty file, a binary
file disguised as text, disallowed extensions (`.py`, `.png`), subfolders and
dates in the names.

The program **rewrites and renames** them. To get the original 18 files back
(from the repository folder):

```bash
python make_test_files.py test_files 18
```

`make_test_files.py` takes `[folder] [count] [seed]`; the same seed always gives
the same files. For a larger test, e.g. 1000 files: `python make_test_files.py big_test 1000`.

`sample_data/file_di_prova.zip` is a second, smaller set of hand-made examples
(`python -m zipfile -e sample_data/file_di_prova.zip sample_data` extracts it).

## The `session.json` file

Saved in the analyzed folder: a list of sessions, one per run on that folder.

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

`changes` is `No changes`, `Changes made: ...` or, in mode 2 when you answer `n`,
`Changes detected but not applied`.

## Repository structure

```
Document-normalizer/
├── README.md
├── LICENSE
├── requirements.txt
├── document_normalizer_colab.ipynb   # Google Colab notebook
├── make_test_files.py                # creates the random sample files
├── test_files/                       # the 18 sample files
├── sample_data/
│   └── file_di_prova.zip             # hand-made sample files
└── src/
    ├── document_normalizer/          # normalization
    │   ├── __init__.py
    │   ├── __main__.py               # python -m document_normalizer
    │   ├── main.py                   # the program: main()
    │   ├── models.py                 # constants, Session and Document classes
    │   └── readers.py                # DocumentReader, TextReader, CSVReader
    └── ricerca/                      # history search
        ├── __init__.py
        ├── __main__.py               # python -m ricerca
        ├── main.py                   # load_history, search_documents, print_results, main()
        ├── models.py                 # same as document_normalizer/models.py
        └── readers.py                # same as document_normalizer/readers.py
```

## Compatibility notes

- Sessions saved by older versions use the `"Excerpt"` key: the search reads both
  `"excerpt"` and `"Excerpt"`.
- Older versions saved `session.json` in the folder the program was started from:
  to search it, type that folder when `ricerca` asks.

## License

MIT - see [LICENSE](LICENSE).
