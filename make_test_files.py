"""Creates a folder of random files to test document-normalizer.

Usage:
    python make_test_files.py [folder] [count] [seed]

Defaults: folder "test_files", 18 files, seed 42 (same seed -> same files).
The folder is deleted and recreated, because document-normalizer rewrites
and renames the files it processes.
"""
import random
import shutil
import sys
from pathlib import Path

WORDS = ("budget meeting report analysis project review notes team sales client "
         "invoice contract summary draft final status update plan roadmap risk "
         "perché città qualità attività però già così").split()
FOREIGN = ["Ελληνικά", "русский текст", "日本語", "中文", "العربية", "Ünïcödé"]
INVISIBLE = ["​", "‌", "‍", "﻿", "­"]
DISALLOWED = [".pdf", ".jpg", ".docx", ".xlsx", ".png", ".json", ".py", ""]


def random_date(rng, separators="/.-"):
  year, month, day = rng.randint(2000, 2030), rng.randint(1, 12), rng.randint(1, 28)
  if rng.random() < 0.5:
    return f"{year}-{month:02d}-{day:02d}"
  sep = rng.choice(separators)
  return f"{day:02d}{sep}{month:02d}{sep}{year}"


def random_name(rng):
  words = rng.sample(WORDS[:20], rng.randint(1, 3))
  if rng.random() < 0.3:
    words = [w.upper() if rng.random() < 0.5 else w for w in words]
  name = rng.choice(["_", "-", " ", "  "]).join(words)
  if rng.random() < 0.3:
    # no "/" in file names: it is a folder separator
    name += rng.choice(["_", " ", "-"]) + random_date(rng, ".-")
  return name


def messy_text(rng):
  lines = []
  for _ in range(rng.randint(1, 12)):
    words = [rng.choice(WORDS) for _ in range(rng.randint(0, 15))]
    if rng.random() < 0.2:
      words.insert(0, random_date(rng))
    if rng.random() < 0.1:
      words.append(rng.choice(FOREIGN))
    line = rng.choice([" ", "  ", "\t", "   "]).join(words)
    if rng.random() < 0.3:
      line = "   " + line + "  \t"
    if rng.random() < 0.2:
      pos = rng.randint(0, len(line))
      line = line[:pos] + rng.choice(INVISIBLE) + line[pos:]
    lines.append(line)
    lines.extend([""] * rng.choice([0, 0, 1, 3]))
  return rng.choice(["\n", "\r\n", "\r"]).join(lines)


def markdown_text(rng):
  return f"#  {rng.choice(WORDS).title()}\n\n\n\n" + messy_text(rng) + "\n\n-  item\n-   item\n"


def csv_text(rng):
  delimiter = rng.choice([",", ";", "\t", "|"])
  columns = rng.randint(2, 25)
  header = [f"{rng.choice(WORDS)}_{i}" for i in range(columns)]
  if rng.random() < 0.15:
    header = [str(rng.randint(1, 999)) for _ in range(columns)]
  rows = [header]
  for _ in range(rng.randint(1, 30)):
    rows.append([rng.choice([str(rng.randint(0, 9999)), f"{rng.uniform(0, 9999):.2f}".replace(".", ","),
                             "  " + rng.choice(WORDS) + "  ", random_date(rng), ""])
                 for _ in range(columns)])
  return rng.choice(["\n", "\r\n"]).join(delimiter.join(row) for row in rows) + "\n"


def encode(rng, text, choice=None):
  if choice is None:
    choice = rng.random()
  if choice < 0.70:
    return text.encode("utf-8")
  if choice < 0.80:
    return b"\xef\xbb\xbf" + text.encode("utf-8")
  if choice < 0.92:
    return text.encode("cp1252", errors="replace")
  return text.encode("utf-16")


# The first files cover every case, so even a small folder has all of them:
# (kind, encoding choice for encode(): 0.0 UTF-8, 0.75 UTF-8 BOM, 0.85 cp1252, 0.95 UTF-16)
FIRST_FILES = [("txt", 0.0), ("txt", 0.85), ("txt", 0.95), ("md", 0.75), ("csv", 0.0),
               ("csv", 0.85), ("empty", None), ("binary", None), ("disallowed", None)]


def make_file(rng, folder, kind=None, encoding=None):
  if kind is None:
    kind = rng.choices(["txt", "md", "csv", "empty", "binary", "disallowed"],
                       weights=[35, 20, 25, 4, 6, 10])[0]
  subfolder = folder / rng.choice(["", "", "", "archive", "archive/2024", "clients"])
  subfolder.mkdir(parents=True, exist_ok=True)
  if kind == "txt":
    ext, data = rng.choice([".txt", ".TXT"]), encode(rng, messy_text(rng), encoding)
  elif kind == "md":
    ext, data = ".md", encode(rng, markdown_text(rng), encoding)
  elif kind == "csv":
    ext, data = ".csv", encode(rng, csv_text(rng), encoding)
  elif kind == "empty":
    ext, data = rng.choice([".txt", ".md", ".csv"]), b""
  elif kind == "binary":
    ext, data = rng.choice([".txt", ".csv"]), bytes(rng.randrange(256) for _ in range(rng.randint(10, 2000)))
  else:
    ext, data = rng.choice(DISALLOWED), bytes(rng.randrange(256) for _ in range(rng.randint(10, 500)))
  path = subfolder / (random_name(rng) + ext)
  counter = 2
  while path.exists():
    path = subfolder / (f"{random_name(rng)} {counter}" + ext)
    counter += 1
  path.write_bytes(data)


def main():
  folder = Path(sys.argv[1] if len(sys.argv) > 1 else "test_files")
  count = int(sys.argv[2]) if len(sys.argv) > 2 else 18
  rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 42)
  if folder.exists():
    shutil.rmtree(folder)
  folder.mkdir(parents=True)
  for index in range(count):
    if index < len(FIRST_FILES):
      make_file(rng, folder, *FIRST_FILES[index])
    else:
      make_file(rng, folder)
  print(f"{count} files created in '{folder}'.")


if __name__ == "__main__":
  main()
