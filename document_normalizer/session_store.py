"""Reading and writing the session history file (session.json by default).

The file is a JSON LIST of sessions, the oldest first:

    [
      {"session_id": 1, "session_date": "...", "documents": {...}},
      {"session_id": 2, "session_date": "...", "documents": {...}}
    ]

Both functions are tolerant: a missing, empty or corrupted file is treated
as "no history yet" instead of stopping the program.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union

from .models import Session

PathLike = Union[str, Path]


def load_history(path: PathLike) -> list[dict[str, Any]]:
    """Returns the list of sessions stored in the file.

    Args:
        path: Path of the history file.

    Returns:
        The sessions found. An old file holding a single session object
        (instead of a list) is wrapped in a list. A missing or unreadable
        file gives an empty list.
    """
    try:
        # UTF-8 explicitly: the file is written with ensure_ascii=False, so it
        # contains real accented letters; without the encoding, Windows would
        # read it with its local code page and break them.
        with open(path, "r", encoding="utf-8") as file:
            content = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    if isinstance(content, dict):
        return [content]
    if isinstance(content, list):
        return content
    return []


def next_session_id(path: PathLike) -> int:
    """Highest session_id already in the history, plus one (1 for a new file)."""
    history = load_history(path)
    # default=0 handles the empty list; .get() handles a session without id.
    highest = max((session.get("session_id", 0) for session in history if isinstance(session, dict)), default=0)
    return highest + 1


#Change(NEW: search a word in the titles of ONE session of the history file - the program uses the session just saved)
def search_titles(path: PathLike, word: str, session_id: int) -> list[dict[str, Any]]:
    """Finds the titles of one session that contain a word.

    The comparison is done in lowercase on both sides (word.lower() in
    title.lower()), so "nota", "NOTA" and "Nota" find the same titles.
    The word may appear anywhere in the title: "verb" finds "2024-03-15 Verbale".

    Only the session with the given id is searched: older sessions are ignored.

    Args:
        path: Path of the history file.
        word: The word to look for (spaces at the ends are ignored).
        session_id: The session to search in.

    Returns:
        One dictionary per matching file, in the order of the session:
        {"title", "file_name", "new_path", "saved"}.
        An empty word, an unknown session or no match gives an empty list.
    """
    needle = word.strip().lower()
    if not needle:
        return []
    for session in load_history(path):
        if isinstance(session, dict) and session.get("session_id") == session_id:
            return [
                {
                    "title": entry.get("title", ""),
                    "file_name": entry.get("file_name", ""),
                    "new_path": entry.get("new_path", ""),
                    "saved": entry.get("saved", False),
                }
                for entry in session.get("documents", {}).values()
                if needle in entry.get("title", "").lower()
            ]
    return []


def append_session(path: PathLike, session: Session) -> None:
    """Adds a session at the end of the history file and writes it back.

    Args:
        path: Path of the history file (created if it does not exist).
        session: The session to store.
    """
    history = load_history(path)
    history.append(session.to_dict())
    with open(path, "w", encoding="utf-8") as file:
        # indent=2 keeps the file readable by a human;
        # ensure_ascii=False writes "città" instead of "città".
        json.dump(history, file, indent=2, ensure_ascii=False)
