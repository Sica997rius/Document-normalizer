"""Command line program: the full run, from folder scan to session.json.

Flow of a run:
  1. Ask to continue, then ask (or receive) the folder to analyze.
  2. List the files: allowed (TXT, CSV, MD) and not allowed.
  3. Process every allowed file: read it, normalize it, compute title,
     date, excerpt. NOTHING is written to disk in this phase; files with
     changes are put in a "pending" list.
  4. Show the pending changes and ask ONCE whether to save all of them.
       yes -> texts are rewritten and files renamed; the JSON gets the new path.
       no  -> disk untouched; the JSON keeps the old path as "new_path".
  5. Append the session to the history file (session.json).
  6. Optionally search words in the titles of the session just saved.

Run it with:
    document-normalizer                 (installed command)
    document-normalizer path/to/folder  (skips the folder question)
    python -m document_normalizer       (without installing the command)
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Callable, NamedTuple, Optional, Sequence

from . import __version__
from .config import BINARY_FILE_NOTE, DEFAULT_SESSION_FILE, YES_ANSWERS
from .csv_reader import CSVReader
from .folder_reader import FileTable, FolderReader
from .models import Document, Session
#Change(search_titles imported for the final title search)
from .session_store import append_session, next_session_id, search_titles


class FileRules(NamedTuple):
    """The functions that decide how one file type is processed.

    TXT and MD use the FolderReader functions; CSV uses the CSVReader ones.
    Keeping them together lets a single function (process_file) handle every
    type, instead of three almost identical loops.

    Attributes:
        label: Heading printed before the files of this type.
        normalize: Text -> normalized text.
        excerpt: Normalized text -> excerpt.
        title: File name without extension -> title.
        date: (normalized text, file name without extension) -> date or None.
        multiline_excerpt: True if the excerpt is printed on several lines (CSV).
    """

    label: str
    normalize: Callable[[str], str]
    excerpt: Callable[[str], str]
    title: Callable[[str], str]
    date: Callable[[str, str], Optional[str]]
    multiline_excerpt: bool


# TXT and MD: date searched in the TEXT, title in "Title Case".
TEXT_RULES = FileRules(
    label="TXT (Text files)",
    normalize=FolderReader.normalize_text,
    excerpt=FolderReader.create_excerpt,
    title=FolderReader.title_from_filename,
    date=lambda text, stem: FolderReader.find_date(text),
    multiline_excerpt=False,
)
MARKDOWN_RULES = TEXT_RULES._replace(label="MD (Markdown)")

# CSV: date searched in the FILE NAME, title = existing name cleaned.
CSV_RULES = FileRules(
    label="CSV (Data files)",
    normalize=CSVReader.normalize_text,
    excerpt=CSVReader.create_excerpt,
    title=CSVReader.title_from_existing,
    date=lambda text, stem: CSVReader.date_from_title(stem),
    multiline_excerpt=True,
)


class PendingChange(NamedTuple):
    """A file whose changes wait for the final confirmation.

    Attributes:
        file_path: Original path of the file.
        file_name: Original file name (with extension).
        ext: Lowercase extension, reused for the new name.
        doc: The analyzed document (title, normalized text, flags).
    """

    file_path: Path
    file_name: str
    ext: str
    doc: Document


def print_file_list(files: dict) -> None:
    """Prints a file table one entry per line, as "[number] name", plus a total.

    Works both for {number: Path} (full paths) and for
    {number: (file_name, extension)} (names only).

    Args:
        files: The table to print.
    """
    if not files:
        print("  (none)")
        return
    for number, item in files.items():
        name = item if isinstance(item, Path) else item[0]
        print(f"  [{number}] {name}")
    print(f"  total: {len(files)}")


def is_yes(answer: str) -> bool:
    """True if the answer means "yes" (see YES_ANSWERS); case and spaces ignored."""
    return answer.strip().lower() in YES_ANSWERS


def process_file(number: int, file_path: Path, file_name: str, ext: str, rules: FileRules) -> Optional[Document]:
    """Reads and analyzes one file, prints the result, writes nothing to disk.

    Args:
        number: The file number in the lists (becomes the document ID).
        file_path: Where the file is.
        file_name: Its name with extension.
        ext: Its lowercase extension.
        rules: How to normalize, title, date and excerpt this file type.

    Returns:
        The analyzed Document, or None if the file is empty.
    """
    raw_text, encoding, is_binary = FolderReader.read_file(file_path)
    if not raw_text:
        print(f"File {file_name} is empty and will be skipped.\n")
        return None

    stem = Path(file_name).stem
    if is_binary:
        # A binary file is never normalized (rewriting it would corrupt it):
        # its content is kept as it is, so "text_changed" stays False.
        normalized_text = raw_text
        word_count = 0
        excerpt = BINARY_FILE_NOTE
        # TXT/MD look for the date in the text, which is unreadable here;
        # CSV looks in the file name, which is still meaningful.
        detected_date = rules.date("", stem) if rules is CSV_RULES else None
    else:
        normalized_text = rules.normalize(raw_text)
        word_count = FolderReader.count_words(normalized_text)
        excerpt = rules.excerpt(normalized_text)
        detected_date = rules.date(normalized_text, stem)

    doc = Document(
        document_id=str(number),
        title=rules.title(stem),
        original_title=file_name,
        word_count=word_count,
        excerpt=excerpt,
        content=normalized_text,
        format=ext,
        path=str(file_path),
        date=detected_date,
        extra={"encoding": encoding},
        original_content=raw_text,
    )

    print(f"Document ID {number} ({file_name}) processed successfully:")
    print(f"  Title: {doc.title}")
    print(f"  Words: {doc.word_count}")
    print(f"  Date found: {doc.date}")
    print(f"  Encoding: {encoding}")
    if rules.multiline_excerpt:
        print("  Excerpt:\n    " + doc.excerpt.replace("\n", "\n    "))
    else:
        print(f"  Excerpt: {doc.excerpt}")
    print(f"  Changes: {doc.changes_made}")
    print("-" * 40)
    return doc


def process_group(
    title_label: str,
    files: FileTable,
    document_list: dict[int, Path],
    rules: FileRules,
    session_documents: dict,
    pending_changes: list[PendingChange],
) -> None:
    """Processes all the files of one type and records them.

    Every processed file gets an entry in session_documents with
    new_path = original path and saved = False; apply_pending_changes()
    updates them if the user saves. Files with changes are added to
    pending_changes. An error on one file is printed and the loop goes on.

    Args:
        title_label: Heading printed before the group.
        files: {number: (file_name, ext)} of this type.
        document_list: {number: path} of the whole folder.
        rules: Processing rules for this type.
        session_documents: Filled in place (key = original full path).
        pending_changes: Filled in place.
    """
    if not files:
        return
    print(f"=== Processing type: {title_label} ===\n")
    for number, (file_name, ext) in files.items():
        file_path = document_list[number]
        try:
            doc = process_file(number, file_path, file_name, ext, rules)
        except Exception as error:  # one broken file must not stop the run
            print(f"Error while processing {file_name}: {error}\n")
            continue
        if doc is None:
            continue
        changes_description = doc.changes_made
        if changes_description != "No changes":
            pending_changes.append(PendingChange(file_path, file_name, ext, doc))
        session_documents[str(file_path)] = {
            "file_name": file_name,
            "title": doc.title,
            "original_path": str(file_path),
            "new_path": str(file_path),
            "changes": [changes_description],
            "saved": False,
        }


def apply_pending_changes(pending_changes: list[PendingChange], session_documents: dict) -> int:
    """Writes the pending changes to disk (to be called only after a "yes").

    For each file: the normalized text is written (UTF-8) if it changed, then
    the file is renamed if the title changed, using a free name
    ("Title (2).txt" if "Title.txt" already exists). The session entry gets
    the new path and saved = True. Each file has its own try: an error on
    one file does not stop the others.

    Args:
        pending_changes: The files to save.
        session_documents: Updated in place.

    Returns:
        How many files were saved successfully.
    """
    saved_count = 0
    for change in pending_changes:
        file_path, file_name, ext, doc = change
        try:
            new_path = file_path
            if doc.text_changed:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(doc.content)
            if doc.title_changed:
                new_path = FolderReader.unique_path(file_path.with_name(doc.title + ext), file_path)
                file_path.rename(new_path)
                doc.path = str(new_path)
            entry = session_documents[str(file_path)]
            entry["new_path"] = str(new_path)
            entry["saved"] = True
            saved_count += 1
            if new_path != file_path:
                print(f"Saved: '{file_name}' -> '{new_path.name}'")
            else:
                print(f"Saved: '{file_name}' (text normalized)")
        except Exception as error:
            print(f"Error while saving {file_name}: {error}")
    return saved_count


#Change(NEW: final step of the flow - optional search of a word in the titles of the session just saved)
def search_titles_interactive(session_file: str, session_id: int) -> None:
    """Offers to search words in the titles of the session just saved.

    Asks once whether to search; then asks a word at a time and prints the
    titles that contain it (lowercase comparison, see search_titles), until
    an empty word (just Enter) is typed.

    Args:
        session_file: Path of the history file.
        session_id: The session just saved (the only one searched).
    """
    if not is_yes(input(f"\nDo you want to search a word in the titles of session {session_id}? (y/n): ")):
        return
    while True:
        word = input("\nWord to search (press Enter to finish): ")
        if not word.strip():
            break
        matches = search_titles(session_file, word, session_id)
        if not matches:
            print(f"No title contains '{word.strip()}'.")
            continue
        print(f"{len(matches)} title(s) contain '{word.strip()}':")
        for match in matches:
            # "(not saved)": the title was proposed but the file was not renamed.
            note = "" if match["saved"] else "  (not saved)"
            print(f"  - {match['title']}  ->  {match['new_path']}{note}")


def build_parser() -> argparse.ArgumentParser:
    """Defines the command line options."""
    parser = argparse.ArgumentParser(
        prog="document-normalizer",
        description="Normalizes the TXT, MD and CSV files of a folder and records each run in a JSON history.",
    )
    parser.add_argument("folder", nargs="?", help="folder to analyze (asked interactively if omitted)")
    parser.add_argument(
        "--session-file",
        default=DEFAULT_SESSION_FILE,
        help=f"history file to create or extend (default: {DEFAULT_SESSION_FILE} in the current directory)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Runs the whole program.

    Args:
        argv: Command line arguments (None = the real ones, sys.argv[1:]).
            Passing a list is useful in tests.

    Returns:
        Exit code: 0 = completed, 1 = the folder does not exist.
    """
    args = build_parser().parse_args(argv)

    input(
        "Before running the normalization, make sure that the files you intend to read\n"
        "in the folders and subfolders of the main folder have an allowed format "
        "(.TXT, .CSV, .MD).\n"
        "Type a character or press Enter to continue: "
    )
    print("\n")
    document_list = FolderReader.open_document_list(args.folder)
    print_file_list(document_list)
    print("")
    if not document_list:
        return 1

    allowed_files = FolderReader.allowed_extensions(document_list)
    disallowed_files = FolderReader.disallowed_extensions(document_list)
    txt_documents = FolderReader.txt_documents(allowed_files)
    csv_documents = FolderReader.csv_documents(allowed_files)
    md_documents = FolderReader.md_documents(allowed_files)

    print("\nThe allowed files are the following: \n")
    print("Text files: ")
    print_file_list(txt_documents)
    print("\nData files: ")
    print_file_list(csv_documents)
    print("\nMarkdown files: ")
    print_file_list(md_documents)
    print("\nThe disallowed files are the following: ")
    print_file_list(disallowed_files)
    print("\n--- Start of document processing and indexing --- \n")

    session_documents: dict = {}
    pending_changes: list[PendingChange] = []
    # Same order as the original program: TXT, then MD, then CSV.
    process_group(TEXT_RULES.label, txt_documents, document_list, TEXT_RULES, session_documents, pending_changes)
    process_group(MARKDOWN_RULES.label, md_documents, document_list, MARKDOWN_RULES, session_documents, pending_changes)
    process_group(CSV_RULES.label, csv_documents, document_list, CSV_RULES, session_documents, pending_changes)

    # One single question for all the files.
    if pending_changes:
        print(f"\n{len(pending_changes)} files have changes to apply:")
        for change in pending_changes:
            print(f"  - {change.file_name}: {change.doc.changes_made}")
        if is_yes(input("\nDo you want to save ALL these changes to disk? (y/n): ")):
            saved_count = apply_pending_changes(pending_changes, session_documents)
            print(f"\nChanges saved for {saved_count} of {len(pending_changes)} files.")
        else:
            print("No changes saved to disk.")
    else:
        print("\nNo changes to apply.")

    #Change(remembers the id of the session saved in this run; stays None if nothing was saved)
    saved_session_id: Optional[int] = None
    if session_documents:
        try:
            session = Session(
                session_id=next_session_id(args.session_file),
                session_date=datetime.now(),
                documents=session_documents,
            )
            append_session(args.session_file, session)
            saved_session_id = session.session_id
            print(f"\nSession {session.session_id} saved successfully to '{args.session_file}'.")
        except Exception as error:
            print(f"Error while saving the global session: {error}")

    #Change(the flow ends with the optional search, only if the session was really saved)
    if saved_session_id is not None:
        search_titles_interactive(args.session_file, saved_session_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
