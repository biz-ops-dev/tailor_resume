from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import date

from .jobpost.flow import build_job_post_from_cli, MissingRequiredFieldsError
from .resume_parse import parse_professional_experience, render_resume_with_new_roles
from .tailor_engine import tailor
from .markdown_rules import normalize_markdown_spacing, validate_markdown
from .notes_rules import strip_notes_from_markdown, validate_notes_placement
from .text_utils import make_contact_table, safe_slug
from .scoring import apply_reordered_core_competencies
from .run_log import append_csv_row
from .text_utils import now_iso_local
from .resume_frontmatter import render_resume_frontmatter
from .config.stopwords import load_stopwords
from .tailor_config import TailorConfig
from .tailor_config import load_config


def build_argparser() -> argparse.ArgumentParser:
  ap = argparse.ArgumentParser()
  ap.add_argument("--resume", required=True, help="Path to resume_base.md")
  ap.add_argument("--out-dir", default=None, help="Directory for outputs (jobpost + tailored resume + report)")
  ap.add_argument("--config", default=None, help="Optional TOML config")

  ap.add_argument("--job-url", default=None, help="Provide job URL directly (skips URL clipboard prompt)")
  ap.add_argument("--job-text", default=None, help="Path to job text file (skips job text clipboard prompt)")

  ap.add_argument("--use-nltk", action="store_true", help="Enable NLTK if installed")
  ap.add_argument("--dry-run", action="store_true")

  # mechanical move of your logging flags (not mandatory for the new flow, but kept)
  ap.add_argument("--log-csv", default=None, help="Append a row to this CSV file each run")
  ap.add_argument("--profile", default="base", help="Label for the resume/profile used (default: base)")
  ap.add_argument("--status", default="", help="Optional submission status to log (drafted/submitted/interview/etc.)")

  return ap

def main() -> int:
  args = build_argparser().parse_args()

  base_resume = Path(args.resume)
  if not base_resume.exists():
    raise FileNotFoundError(f"Resume not found: {base_resume}")

  # ---- load config FIRST ----
  default_cfg = Path(__file__).resolve().parent / "config/tailor_resume.toml"
  cfg_path = Path(args.config) if args.config else default_cfg
  cfg = load_config(cfg_path if cfg_path.exists() else None)

  # enforce mandatory contact info
  if not (cfg.contact_email.strip() and cfg.contact_location.strip() and cfg.contact_phone.strip()):
    raise RuntimeError("Contact info is mandatory in tailor_resume.toml")

  # stopwords (global list)
  STOPWORDS_PATH = Path(__file__).resolve().parent / "config" / "stopwords.yaml"
  cfg.stopwords = load_stopwords(STOPWORDS_PATH)

  if args.use_nltk:
    cfg.use_nltk = True

  # ---- build job post -----

  try:
    job_result = build_job_post_from_cli(args, cfg)
  except MissingRequiredFieldsError as e:
    raise RuntimeError(
      f"Job post missing required fields: {', '.join(e.missing)} "
      f"(source={e.source}). Re-copy the LinkedIn post and try again."
    )

  post = job_result.post
  out_dir = job_result.out_dir
  jobpost_path = job_result.jobpost_path

  # apply stopwords delta HERE in CLI
  cfg.stopwords = set(cfg.stopwords) | job_result.stopwords_delta

  # ---- tailor resume ----
  intermediate_md_resume = base_resume.read_text(encoding="utf-8")

  # mandatory contact line injection
  contact_block = make_contact_table(cfg.contact_email, cfg.contact_location, cfg.contact_phone)
  if not contact_block:
    raise RuntimeError("Contact table rendered empty (contact info missing in config).")

  if "{{CONTACT_LINE}}" in intermediate_md_resume:
    intermediate_md_resume = intermediate_md_resume.replace("{{CONTACT_LINE}}", contact_block.rstrip() + "\n", 1)
  else:
    raise RuntimeError("Missing {{CONTACT_LINE}} placeholder in base resume.")

  # doc is dataclass ResumeDoc
  # ¿ why can't make "doc:ResumeDoc"
  doc = parse_professional_experience(intermediate_md_resume)


  # doc is dataclass ResumeDoc
  # post: JobPost
  new_roles, report = tailor(doc, post.description, cfg)
  out_md = render_resume_with_new_roles(doc, new_roles)

  # Apply CORE_COMPETENCIES reorder
  reordered_competencies = report.get("core_competencies_reordered") or []
  if reordered_competencies:
    out_lines = out_md.splitlines()
    out_lines = apply_reordered_core_competencies(out_lines, reordered_competencies)
    out_md = "\n".join(out_lines).rstrip() + "\n"

  out_md = normalize_markdown_spacing(out_md)

  md_errors = validate_markdown(out_md)
  if md_errors:
    raise RuntimeError("Markdown validation failed:\n" + "\n".join(f"- {e}" for e in md_errors[:25]))

  out_md = strip_notes_from_markdown(out_md)

  note_errors = validate_notes_placement(out_md)
  if note_errors:
    raise RuntimeError("Note validation failed:\n" + "\n".join(f"- {e}" for e in note_errors[:50]))

  # ---- output names ----
  date_prefix = post.date_pulled.strftime("%Y-%m-%d")
  name_slug = safe_slug(f"{post.company}_{post.title}")

  resume_out = out_dir / f"{date_prefix}_resume_{name_slug}.md"
  report_out = out_dir / f"{date_prefix}_report_{name_slug}.json"

  if not args.dry_run:
    frontmatter = render_resume_frontmatter(
      job_title=post.title,           # (and inside render_resume_frontmatter you will rename key to job_title)
      company=post.company,
      date_pulled=post.date_pulled,
      source=post.source,
      url=post.url,
      profile=args.profile,
    )
    out_md = frontmatter + out_md
    resume_out.write_text(out_md, encoding="utf-8")
    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

  # ---- CSV log (default from config, override by CLI) ----
  csv_path = None
  if args.log_csv:
    csv_path = Path(args.log_csv)
  elif getattr(cfg, "paths_csv_log", ""):
    csv_path = Path(cfg.paths_csv_log)

  if csv_path:
    missing = report.get("missing_keywords", [])
    missing_top = "; ".join([m.get("keyword", "") for m in missing[:10]]) if isinstance(missing, list) else ""

    kept_count = 0
    dropped_count = 0
    for r in report.get("roles", []):
      kept_count += len(r.get("kept", []))
      dropped_count += len(r.get("dropped", []))

    row = {
      "timestamp": now_iso_local(),
      "profile": args.profile,
      "submission_status": args.status,
      "job_file": str(jobpost_path),
      "resume_in": str(base_resume),
      "resume_out": str(resume_out),
      "report_out": str(report_out),
      "use_nltk": str(cfg.use_nltk),
      "per_role_keep": str(cfg.per_role_keep),
      "min_per_role_keep": str(cfg.min_per_role_keep),
      "drop_below_score": str(cfg.drop_below_score),
      "kept_bullets_total": str(kept_count),
      "dropped_bullets_total": str(dropped_count),
      "missing_keywords_top10": missing_top,
    }
    header = list(row.keys())

    if not args.dry_run:
      append_csv_row(csv_path, header, row)

  print(f"Job post: {jobpost_path}")
  print(f"Resume out: {resume_out}")
  print(f"Report out: {report_out}")
  return 0