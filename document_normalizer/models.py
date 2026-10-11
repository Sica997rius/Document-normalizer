"""Data models: what a processed document and a session look like.

These are plain containers (dataclasses). They hold data and answer simple
questions about it ("did the title change?"), but they never read or write
files: that is the job of the readers and of the command line module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class Document:
    """Everything the program knows about one analyzed file.

    Attributes:
        document_id: Progressive number assigned when the folder is scanned.
            It is the same number printed in the file lists.
        title: Title computed for the file. If it differs from the current
            file name, the file will be renamed (after confirmation).
        original_title: File name on disk at the moment it was read,
            extension included (e.g. "my_notes.txt").
        word_count: Number of words in the normalized text (0 for binary files).
        excerpt: Short preview: the first part of the text for TXT/MD files,
            the first row as "column: value" lines for CSV files.
        content: The normalized text (for binary files: the original content,
            untouched).
        format: Lowercase extension of the file (".txt", ".md", ".csv").
        path: Path of the file on disk. It is updated after a rename.
        date: Date found (TXT/MD: in the text, CSV: in the file name only),
            in "YYYY-MM-DD" format, or None.
        extra: Free metadata. The program stores the detected text encoding
            here, under the "encoding" key.
        original_content: The text exactly as read from disk. It is compared
            with "content" to know whether normalization changed anything.
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
    extra: dict[str, Any] = field(default_factory=dict)
    original_content: Optional[str] = None

    @property
    def title_changed(self) -> bool:
        """True if the computed title differs from the current file name.

        The comparison uses the name WITHOUT extension ("stem"): the title
        "My Notes" must be compared with "my_notes", not with "my_notes.txt".
        """
        return self.title != Path(self.path).stem

    @property
    def text_changed(self) -> bool:
        """True if normalization produced a text different from the original."""
        return self.original_content is not None and self.content != self.original_content

    @property
    def changes_made(self) -> str:
        """Human readable summary of the pending changes.

        Returns:
            "Changes made: title was changed, text was normalized" (or only
            one of the two parts), or "No changes".
        """
        changes = []
        if self.title_changed:
            changes.append("title was changed")
        if self.text_changed:
            changes.append("text was normalized")
        if changes:
            return "Changes made: " + ", ".join(changes)
        return "No changes"

    def to_dict(self) -> dict[str, Any]:
        """Returns all the fields as a plain dictionary (handy for JSON)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        """Builds a Document from a dictionary produced by to_dict()."""
        return cls(**data)


@dataclass
class Session:
    """One run of the program.

    Every run appends one session to the history file (session.json).

    Attributes:
        session_id: Progressive number: 1 for the first run, then 2, 3, ...
        session_date: When the session was recorded.
        documents: One entry per processed file. The KEY is the full original
            path of the file (two files with the same name in different
            folders must not overwrite each other). Each value contains:
            file_name, title, original_path, new_path, changes, saved.
    """

    session_id: int
    session_date: datetime
    documents: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Dictionary written to the JSON file (the date as ISO text)."""
        return {
            "session_id": self.session_id,
            "session_date": self.session_date.isoformat(),
            "documents": self.documents,
        }
