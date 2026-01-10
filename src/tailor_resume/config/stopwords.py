from __future__ import annotations

from pathlib import Path
import yaml


def load_stopwords(path: Path) -> set[str]:
  if not path.exists():
    raise FileNotFoundError(f"Stopwords file not found: {path}")

  data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

  out: set[str] = set()

  for group in data.values():
    if isinstance(group, list):
      for w in group:
        if isinstance(w, str):
          out.add(w.strip().lower())

  return out
