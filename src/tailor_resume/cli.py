from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import date

from .clipboard_flow import capture_from_clipboard, ensure_title_company
from .linkedin_parser import is_linkedin_url, parse_linkedin_job_post
from .models import JobPost
from .jobpost_io import write_jobpost
from .resume_parse import parse_resume, render_resume_with_new_roles
from .tailor_engine import tailor
from .markdown_rules import normalize_markdown_spacing, validate_markdown
from .notes_rules import strip_notes_from_markdown, validate_notes_placement
from .text_utils import make_contact_table, safe_slug
from .scoring import apply_reordered_core_competencies
from .run_log import append_csv_row
from .text_utils import now_iso_local
from .resume_frontmatter import render_resume_frontmatter
from .config.stopwords import load_stopwords
from .text_utils import company_stopwords
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

  resume_path = Path(args.resume)
  if not resume_path.exists():
    raise FileNotFoundError(f"Resume not found: {resume_path}")

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

  # ---- capture job url + text ----
  if args.job_url and args.job_text:
    url = args.job_url.strip()
    job_text = Path(args.job_text).read_text(encoding="utf-8")
  else:
    cap = capture_from_clipboard()
    url = cap.url
    job_text = cap.description

  # ---- parse job post ----
  if is_linkedin_url(url):
    post = parse_linkedin_job_post(url=url, full_text=job_text)
  else:
    from datetime import date
    post = JobPost(
      url=url.strip(),
      source="other",
      date_pulled=date.today(),
      title="",
      company="",
      description=job_text.strip(),
      attributes={},
    )

  # ---- enforce required title/company ----
  title, company = ensure_title_company(title=post.title, company=post.company)
  post.title = title
  post.company = company

  # ---- company-specific stopwords (per run) ----
  cfg.stopwords = set(cfg.stopwords)
  cfg.stopwords |= company_stopwords(post.company)

  # ---- compute output directory (NOW safe: needs cfg + post) ----
  base_out_root = Path(args.out_dir) if args.out_dir else Path(cfg.paths_out_root)

  today = post.date_pulled
  month_dir = f"{today:%m}-{today:%B}"           # 01-January
  day_dir = f"{today:%d}-{post.company.strip()}" # 09-Acme Corp

  out_dir = base_out_root / month_dir / day_dir
  out_dir.mkdir(parents=True, exist_ok=True)

  # ---- write job post markdown ----
  if not args.dry_run:
    jobpost_path = write_jobpost(out_dir, post)
  else:
    jobpost_path = out_dir / "DRY_RUN_jobpost.md"

  # ---- tailor resume ----
  md_text = resume_path.read_text(encoding="utf-8")

  # mandatory contact line injection
  contact_block = make_contact_table(cfg.contact_email, cfg.contact_location, cfg.contact_phone)
  if not contact_block:
    raise RuntimeError("Contact table rendered empty (contact info missing in config).")

  if "{{CONTACT_LINE}}" in md_text:
    md_text = md_text.replace("{{CONTACT_LINE}}", contact_block.rstrip() + "\n", 1)
  else:
    raise RuntimeError("Missing {{CONTACT_LINE}} placeholder in base resume.")

  doc = parse_resume(md_text)
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
      "resume_in": str(resume_path),
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