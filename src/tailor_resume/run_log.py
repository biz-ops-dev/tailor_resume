# mechanical move of CSV logging helpers

from __future__ import annotations

from pathlib import Path


def append_csv_row(csv_path: Path, header: list[str], row: dict) -> None:
  csv_path.parent.mkdir(parents=True, exist_ok=True)
  exists = csv_path.exists()
  with csv_path.open("a", encoding="utf-8", newline="") as f:
    if not exists:
      f.write(",".join(header) + "\n")
    values: list[str] = []
    for h in header:
      v = str(row.get(h, ""))
      if any(ch in v for ch in [",", '"', "\n", "\r"]):
        v = '"' + v.replace('"', '""') + '"'
      values.append(v)
    f.write(",".join(values) + "\n")
