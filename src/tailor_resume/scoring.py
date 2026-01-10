from __future__ import annotations

from typing import Iterable

from .tailor_config import TailorConfig
from .text_utils import (
  normalize_text,
  phrase_hits,
  starts_with_action_verb,
  is_generic,
  tok_fn,
  metric_regex,
)


def score_bullet(
  bullet: str,
  job_text: str,
  cfg: TailorConfig,
  job_terms_auto: list[str],
) -> tuple[float, dict]:
  b = bullet.strip()
  b_norm = normalize_text(b)

  tf = tok_fn(cfg)
  b_toks = set(tf(b, cfg.stopwords))
  j_toks = set(tf(job_text, cfg.stopwords))
  overlap = len(b_toks & j_toks)

  required_hits = phrase_hits(b, cfg.required_terms)
  nice_hits = phrase_hits(b, cfg.nice_to_have_terms)
  domain_hits = phrase_hits(b, cfg.domain_terms)

  auto_hits = sum(1 for term in job_terms_auto if term in b_norm)

  metric = 1 if metric_regex().search(b) else 0
  action = 1 if starts_with_action_verb(b, cfg.action_verbs) else 0
  generic = 1 if is_generic(b, cfg.generic_penalties) else 0
  length_pen = 1 if len(b) > 240 else 0

  score = 0.0
  score += cfg.w_overlap * overlap
  score += cfg.w_required * required_hits
  score += cfg.w_nice * nice_hits
  score += cfg.w_domain * domain_hits
  score += (cfg.w_overlap * 0.6) * auto_hits
  score += cfg.w_metric * metric
  score += cfg.w_action_verb * action
  score -= cfg.w_generic_penalty * generic
  score -= cfg.w_length_penalty * length_pen

  details = {
    "overlap": overlap,
    "required_hits": required_hits,
    "nice_hits": nice_hits,
    "domain_hits": domain_hits,
    "auto_hits": auto_hits,
    "metric": metric,
    "action_verb": action,
    "generic_penalty": generic,
    "length_penalty": length_pen,
  }
  return score, details


def resume_mentions_any(text: str, phrases: Iterable[str]) -> bool:
  t = normalize_text(text)
  return any(normalize_text(p).strip() in t for p in phrases if normalize_text(p).strip())


def job_mentions_any(job_text: str, triggers: Iterable[str]) -> bool:
  return resume_mentions_any(job_text, triggers)


def pick_best_matching_bullet(
  bullets_scored: list[tuple[float, str, dict]],
  phrases: list[str],
) -> tuple[float, str, dict] | None:
  best = None
  for s, b, d in bullets_scored:
    if phrase_hits(b, phrases) > 0:
      if best is None or s > best[0]:
        best = (s, b, d)
  return best


# ----------------------------
# CORE_COMPETENCIES reorder
# ----------------------------

def extract_core_competencies(lines: list[str]) -> tuple[int | None, int | None, list[str]]:
  start = None
  end = None
  items: list[str] = []

  for i, line in enumerate(lines):
    if line.startswith("## ") and line[3:].strip().lower() == "core_competencies":
      start = i
      continue
    if start is not None and i > start and line.startswith("## "):
      end = i
      break

  if start is None:
    return None, None, []

  end = end if end is not None else len(lines)
  for ln in lines[start + 1:end]:
    if ln.startswith("- "):
      items.append(ln)

  return start, end, items


def score_competency(item: str, job_text: str, cfg: TailorConfig, job_terms_auto: list[str]) -> float:
  tf = tok_fn(cfg)
  overlap = len(set(tf(item, cfg.stopwords)) & set(tf(job_text, cfg.stopwords)))
  required_hits = phrase_hits(item, cfg.required_terms)
  nice_hits = phrase_hits(item, cfg.nice_to_have_terms)
  domain_hits = phrase_hits(item, cfg.domain_terms)
  t_norm = normalize_text(item)
  auto_hits = sum(1 for term in job_terms_auto if term in t_norm)

  score = 0.0
  score += cfg.w_overlap * overlap
  score += cfg.w_required * required_hits
  score += cfg.w_nice * nice_hits
  score += cfg.w_domain * domain_hits
  score += (cfg.w_overlap * 0.5) * auto_hits
  return score


def apply_reordered_core_competencies(lines: list[str], reordered: list[str]) -> list[str]:
  if not reordered:
    return lines
  start, end, _ = extract_core_competencies(lines)
  if start is None or end is None:
    return lines
  return lines[:start + 1] + reordered + lines[end:]