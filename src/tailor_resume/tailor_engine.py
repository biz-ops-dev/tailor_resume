from __future__ import annotations

from .tailor_config import TailorConfig
from .models import ResumeDoc, Role
from .job_terms import top_terms_from_job
from .text_utils import normalize_text
from .scoring import (
  score_bullet,
  job_mentions_any,
  pick_best_matching_bullet,
  extract_core_competencies,
  score_competency,
)


def missing_keywords(
  resume_text: str,
  job_text: str,
  cfg: TailorConfig,
  job_terms_auto: list[str],
) -> list[dict]:
  resume_norm = normalize_text(resume_text)

  seen: set[str] = set()
  candidates: list[tuple[str, str]] = []

  def add_many(items, source: str) -> None:
    for it in items:
      k = normalize_text(it).strip()
      if not k or k in seen:
        continue
      seen.add(k)
      candidates.append((k, source))

  add_many(cfg.required_terms, "required")
  add_many(cfg.domain_terms, "domain")
  add_many(cfg.nice_to_have_terms, "nice_to_have")
  add_many(job_terms_auto, "auto")

  missing: list[tuple[str, str]] = []
  for k, src in candidates:
    if k not in resume_norm:
      missing.append((k, src))

  job_norm = normalize_text(job_text)
  ranked = sorted(missing, key=lambda ks: (job_norm.count(ks[0]), len(ks[0])), reverse=True)
  return [{"keyword": k, "source": src, "job_count": job_norm.count(k)} for k, src in ranked]


def tailor(doc: ResumeDoc, job_text: str, cfg: TailorConfig) -> tuple[list[Role], dict]:
  job_terms_auto = top_terms_from_job(job_text, cfg)

  resume_text_original = "\n".join(doc.lines)
  missing = missing_keywords(
    resume_text=resume_text_original,
    job_text=job_text,
    cfg=cfg,
    job_terms_auto=job_terms_auto,
  )

  report: dict = {
    "use_nltk": cfg.use_nltk,
    "job_terms_auto": job_terms_auto,
    "missing_keywords": missing,
    "guardrails": cfg.guardrails,
    "roles": [],
    "config": {
      "per_role_keep": cfg.per_role_keep,
      "min_per_role_keep": cfg.min_per_role_keep,
      "drop_below_score": cfg.drop_below_score,
    },
  }

  new_roles: list[Role] = []
  for role in doc.roles:
    scored: list[tuple[float, str, dict]] = []
    for b in role.bullet_lines:
      s, details = score_bullet(b, job_text, cfg, job_terms_auto)
      scored.append((s, b, details))

    scored_sorted = sorted(scored, key=lambda t: t[0], reverse=True)

    kept: list[tuple[float, str, dict]] = []
    dropped: list[tuple[float, str, dict]] = []

    for s, b, details in scored_sorted:
      if s < cfg.drop_below_score:
        dropped.append((s, b, details))
      else:
        kept.append((s, b, details))

    if len(kept) < cfg.min_per_role_keep:
      need = cfg.min_per_role_keep - len(kept)
      dropped_sorted = sorted(dropped, key=lambda t: t[0], reverse=True)
      kept.extend(dropped_sorted[:need])
      dropped = dropped_sorted[need:]

    guardrail_applied: list[dict] = []
    for gr in cfg.guardrails:
      triggers = gr.get("triggers", [])
      must_phrases = gr.get("must_keep_phrases", [])
      min_keep = int(gr.get("min_keep", 1))

      if not triggers or not must_phrases or min_keep <= 0:
        continue
      if not job_mentions_any(job_text, triggers):
        continue

      kept_match_count = sum(1 for _, b, _ in kept if any(p in b.lower() for p in must_phrases))
      if kept_match_count >= min_keep:
        continue

      promoted = None
      best_from_dropped = pick_best_matching_bullet(dropped, must_phrases)
      if best_from_dropped is not None:
        s_best, b_best, d_best = best_from_dropped
        dropped = [(s, b, d) for (s, b, d) in dropped if b != b_best]
        kept.append((s_best, b_best, d_best))
        promoted = b_best

      kept_match_count = sum(1 for _, b, _ in kept if any(p in b.lower() for p in must_phrases))
      if kept_match_count < min_keep:
        for s, b, d in scored_sorted:
          if any(p in b.lower() for p in must_phrases) and all(b != kb for _, kb, _ in kept):
            kept.append((s, b, d))
            promoted = promoted or b
            kept_match_count += 1
            if kept_match_count >= min_keep:
              break

      if promoted:
        guardrail_applied.append({"name": gr.get("name", "unnamed"), "promoted_bullet": promoted})

    kept = sorted(kept, key=lambda t: t[0], reverse=True)
    kept = kept[:cfg.per_role_keep]

    kept_sorted_lines = [b for _, b, _ in kept]

    new_role = Role(
      role_header=role.role_header,
      company_header=role.company_header,
      other_lines=list(role.other_lines),
      bullet_lines=kept_sorted_lines
    )
    new_roles.append(new_role)

    report["roles"].append({
      "role_header": role.role_header,
      "company_header": role.company_header,
      "guardrails_applied": guardrail_applied,
      "kept": [{"score": round(s, 3), "bullet": b, "details": d} for s, b, d in kept],
      "dropped": [{"score": round(s, 3), "bullet": b, "details": d} for s, b, d in dropped],
    })

  cc_start, cc_end, cc_items = extract_core_competencies(doc.lines)
  reordered_competencies: list[str] = []
  if cc_items:
    scored_cc = [(score_competency(it, job_text, cfg, job_terms_auto), it) for it in cc_items]
    scored_cc.sort(key=lambda t: t[0], reverse=True)
    reordered_competencies = [it for _, it in scored_cc]
  report["core_competencies_reordered"] = reordered_competencies

  return new_roles, report
