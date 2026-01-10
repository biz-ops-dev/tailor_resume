from __future__ import annotations

from typing import Iterable

from .tailor_config import TailorConfig
from .text_utils import NLTK_AVAILABLE, normalize_text, tokens_simple, tokens_nltk, _WORD_RE


def extract_job_noun_phrases(job_text: str, stopwords: set[str]) -> list[str]:
  if not NLTK_AVAILABLE:
    return []

  import nltk
  from nltk import pos_tag, word_tokenize

  t = normalize_text(job_text)
  raw = word_tokenize(t)
  tagged = pos_tag(raw)

  grammar = r"NP: {<JJ.*>*<NN.*>+}"
  chunker = nltk.RegexpParser(grammar)
  tree = chunker.parse(tagged)

  phrases: set[str] = set()
  for subtree in tree.subtrees(filter=lambda st: st.label() == "NP"):
    words = [w.lower() for w, _tag in subtree.leaves()]
    cleaned: list[str] = []
    for w in words:
      if not _WORD_RE.fullmatch(w):
        continue
      if w in stopwords:
        continue
      cleaned.append(w)

    if not cleaned:
      continue
    if 2 <= len(cleaned) <= 4:
      phrase = " ".join(cleaned).strip()
      if sum(1 for x in cleaned if len(x) >= 3) >= 2:
        phrases.add(phrase)

  return sorted(phrases)


def top_terms_from_job_simple(job_text: str, stopwords: set[str], max_terms: int) -> list[str]:
  toks = tokens_simple(job_text, stopwords)
  freq: dict[str, int] = {}
  for t in toks:
    if len(t) <= 2:
      continue
    freq[t] = freq.get(t, 0) + 1
  ranked = sorted(freq.items(), key=lambda kv: (kv[1], len(kv[0])), reverse=True)
  return [k for k, _ in ranked[:max_terms]]


def top_terms_from_job_nltk(job_text: str, stopwords: set[str], max_terms: int) -> list[str]:
  nps = extract_job_noun_phrases(job_text, stopwords)
  toks = tokens_nltk(job_text, stopwords)
  freq: dict[str, int] = {}
  for t in toks:
    if len(t) <= 2:
      continue
    freq[t] = freq.get(t, 0) + 1
  ranked = sorted(freq.items(), key=lambda kv: (kv[1], len(kv[0])), reverse=True)
  single_terms = [k for k, _ in ranked]

  out: list[str] = []
  seen: set[str] = set()
  for it in nps + single_terms:
    it2 = normalize_text(it).strip()
    if not it2 or it2 in seen:
      continue
    seen.add(it2)
    out.append(it2)
    if len(out) >= max_terms:
      break
  return out


def top_terms_from_job(job_text: str, cfg: TailorConfig) -> list[str]:
  if cfg.use_nltk:
    return top_terms_from_job_nltk(job_text, cfg.stopwords, cfg.max_auto_terms)
  return top_terms_from_job_simple(job_text, cfg.stopwords, cfg.max_auto_terms)
