from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from .tailor_config import TailorConfig

# ----------------------------
# Optional NLTK (centralized here)
# ----------------------------
NLTK_AVAILABLE = False
try:
  import nltk  # noqa: F401
  from nltk import pos_tag, word_tokenize
  from nltk.stem import WordNetLemmatizer
  NLTK_AVAILABLE = True
except Exception:
  NLTK_AVAILABLE = False

_LEM = WordNetLemmatizer() if NLTK_AVAILABLE else None


_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-\+\/]*")
_METRIC_RE = re.compile(r"(\$?\d[\d,]*)(\.\d+)?\s*(%|k|m|b|arr|mrr)?\b", re.IGNORECASE)


def normalize_text(s: str) -> str:
  s = s.lower()
  s = s.replace("–", "-").replace("—", "-")
  return s


def tokens_simple(s: str, stopwords: set[str]) -> list[str]:
  s = normalize_text(s)
  out: list[str] = []
  for m in _WORD_RE.finditer(s):
    w = m.group(0).lower().strip("-+/")
    if not w or w in stopwords:
      continue
    if len(w) > 4 and w.endswith("s"):
      w2 = w[:-1]
      if w2 not in stopwords:
        w = w2
    out.append(w)
  return out


def _penn_to_wn(tag: str) -> str:
  if tag.startswith("J"):
    return "a"
  if tag.startswith("V"):
    return "v"
  if tag.startswith("N"):
    return "n"
  if tag.startswith("R"):
    return "r"
  return "n"


def tokens_nltk(s: str, stopwords: set[str]) -> list[str]:
  if not NLTK_AVAILABLE:
    return tokens_simple(s, stopwords)

  t = normalize_text(s)
  raw = word_tokenize(t)
  tagged = pos_tag(raw)

  out: list[str] = []
  for w, tag in tagged:
    w = w.lower().strip()
    if not _WORD_RE.fullmatch(w):
      continue
    if w in stopwords:
      continue
    wn_pos = _penn_to_wn(tag)
    lemma = _LEM.lemmatize(w, wn_pos) if _LEM else w
    if len(lemma) <= 2 or lemma in stopwords:
      continue
    if len(lemma) > 4 and lemma.endswith("s"):
      lemma2 = lemma[:-1]
      if lemma2 and lemma2 not in stopwords:
        lemma = lemma2
    out.append(lemma)
  return out


def tok_fn(cfg: TailorConfig):
  return tokens_nltk if cfg.use_nltk else tokens_simple


def phrase_hits(text: str, phrases: Iterable[str]) -> int:
  if not phrases:
    return 0
  t = normalize_text(text)
  hits = 0
  for p in phrases:
    p2 = normalize_text(p).strip()
    if not p2:
      continue
    if p2 in t:
      hits += 1
  return hits


def starts_with_action_verb(bullet: str, verbs: set[str]) -> bool:
  t = normalize_text(bullet).lstrip("-").strip()
  first = t.split(" ", 1)[0] if t else ""
  first = first.strip(",:;.")
  return first in verbs


def is_generic(bullet: str, generic_phrases: set[str]) -> bool:
  t = normalize_text(bullet)
  return any(g in t for g in generic_phrases)


def safe_slug(s: str) -> str:
  s = s.strip().lower()
  s = s.replace(" ", "_")
  s = re.sub(r"[^a-z0-9_\-]+", "", s)
  s = re.sub(r"_+", "_", s)
  return s.strip("_-")


def now_iso_local() -> str:
  return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def make_contact_table(email: str, location: str, phone: str) -> str:
  email = email.strip()
  location = location.strip()
  phone = phone.strip()

  if not (email or location or phone):
    return ""

  return (
    f"| {email} | {location} | {phone} |\n"
    f"|:--|:--:|--:|\n"
  )

"""
def make_contact_table(email: str, location: str, phone: str) -> str:
  email = email.strip()
  location = location.strip()
  phone = phone.strip()

  if not (email or location or phone):
    return ""

  return (
    "| Email | Location | Phone |\n"
    "|:--|:--:|--:|\n"
    f"| {email} | {location} | {phone} |\n"
  )
"""


def metric_regex():
  return _METRIC_RE

import re


