"""Minimal PEP 517 / PEP 660 build backend, standard library only.

pip normally downloads setuptools to build the package; with this backend
"pip install ." and "pip install -e ." work offline, in a clean environment
(no setuptools needed). It reads the [project] table of pyproject.toml and
packs every package found in src/.
"""
import base64
import hashlib
import io
import re
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


# ---------- pyproject.toml ----------
def _read_project():
  """Reads the fields used here from pyproject.toml (no tomllib on Python < 3.11)."""
  text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
  tables, current = {}, None
  for line in text.splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
      continue
    header = re.fullmatch(r"\[([^\]]+)\]", line)
    if header:
      current = tables.setdefault(header.group(1).strip(), {})
      continue
    pair = re.fullmatch(r'"?([\w.-]+)"?\s*=\s*"(.*)"', line)
    if pair and current is not None:
      current[pair.group(1)] = pair.group(2)
  project = tables.get("project", {})
  return {
    "name": project["name"],
    "version": project["version"],
    "description": project.get("description", ""),
    "readme": project.get("readme"),
    "requires_python": project.get("requires-python"),
    "scripts": tables.get("project.scripts", {}),
  }


def _dist_name(project):
  return re.sub(r"[-_.]+", "_", project["name"]).lower()


def _metadata(project):
  lines = [
    "Metadata-Version: 2.1",
    f"Name: {project['name']}",
    f"Version: {project['version']}",
    f"Summary: {project['description']}",
  ]
  if project["requires_python"]:
    lines.append(f"Requires-Python: {project['requires_python']}")
  body = ""
  if project["readme"]:
    lines.append("Description-Content-Type: text/markdown")
    body = (ROOT / project["readme"]).read_text(encoding="utf-8")
  return "\n".join(lines) + "\n\n" + body


def _entry_points(project):
  if not project["scripts"]:
    return ""
  return "[console_scripts]\n" + "".join(f"{k} = {v}\n" for k, v in project["scripts"].items())


def _packages():
  return [p for p in sorted(SRC.iterdir()) if (p / "__init__.py").is_file()]


# ---------- wheel ----------
def _write_wheel(wheel_directory, files):
  """files: list of (archive name, bytes). Adds dist-info and RECORD."""
  project = _read_project()
  dist = f"{_dist_name(project)}-{project['version']}"
  dist_info = f"{dist}.dist-info"
  files = list(files) + [
    (f"{dist_info}/METADATA", _metadata(project).encode("utf-8")),
    (f"{dist_info}/WHEEL", b"Wheel-Version: 1.0\nGenerator: document-normalizer _build\n"
                           b"Root-Is-Purelib: true\nTag: py3-none-any\n"),
  ]
  entry_points = _entry_points(project)
  if entry_points:
    files.append((f"{dist_info}/entry_points.txt", entry_points.encode("utf-8")))
  record = []
  for name, data in files:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    record.append(f"{name},sha256={digest},{len(data)}")
  record.append(f"{dist_info}/RECORD,,")
  files.append((f"{dist_info}/RECORD", ("\n".join(record) + "\n").encode("utf-8")))

  wheel_name = f"{dist}-py3-none-any.whl"
  with zipfile.ZipFile(Path(wheel_directory) / wheel_name, "w", zipfile.ZIP_DEFLATED) as wheel:
    for name, data in files:
      wheel.writestr(name, data)
  return wheel_name


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
  files = []
  for package in _packages():
    for path in sorted(package.rglob("*.py")):
      if "__pycache__" not in path.parts:
        files.append((path.relative_to(SRC).as_posix(), path.read_bytes()))
  return _write_wheel(wheel_directory, files)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
  """PEP 660: the wheel only holds a .pth file pointing to src/."""
  project = _read_project()
  return _write_wheel(wheel_directory, [(f"__editable__.{_dist_name(project)}.pth",
                                         (str(SRC) + "\n").encode("utf-8"))])


def get_requires_for_build_wheel(config_settings=None):
  return []


def get_requires_for_build_editable(config_settings=None):
  return []


def get_requires_for_build_sdist(config_settings=None):
  return []


# ---------- sdist ----------
def build_sdist(sdist_directory, config_settings=None):
  project = _read_project()
  base = f"{_dist_name(project)}-{project['version']}"
  sources = [ROOT / "pyproject.toml", ROOT / "README.md", ROOT / "requirements.txt", Path(__file__)]
  for package in _packages():
    sources += [p for p in sorted(package.rglob("*.py")) if "__pycache__" not in p.parts]
  sdist_name = f"{base}.tar.gz"
  with tarfile.open(Path(sdist_directory) / sdist_name, "w:gz") as sdist:
    for path in sources:
      if path.is_file():
        sdist.add(path, arcname=f"{base}/{path.relative_to(ROOT).as_posix()}")
    pkg_info = _metadata(project).encode("utf-8")
    info = tarfile.TarInfo(f"{base}/PKG-INFO")
    info.size = len(pkg_info)
    sdist.addfile(info, io.BytesIO(pkg_info))
  return sdist_name
