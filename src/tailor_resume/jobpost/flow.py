# jobpost_flow.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
import re

from ..clipboard_flow import capture_from_clipboard
from .io import write_jobpost
from .types import JobPost

from ..text_utils import safe_slug
from .linkedin import parse_linkedin_job_post


_LINKEDIN_HOST_RE = re.compile(r"(^|https?://)(www\.)?linkedin\.com/", re.IGNORECASE)


@dataclass
class JobPostBuildResult:
  post: JobPost
  out_dir: Path
  jobpost_path: Path
  stopwords_delta: set[str]


class MissingRequiredFieldsError(ValueError):
  def __init__(self, missing: list[str], *, source: str, url: str):
    self.missing = missing
    self.source = source
    self.url = url
    super().__init__(f"Missing required fields: {', '.join(missing)}")


def is_linkedin_url(url: str) -> bool:
  return bool(_LINKEDIN_HOST_RE.search((url or "").strip()))


def _compute_out_dir(*, base_out_root: Path, post: JobPost) -> Path:
  today = post.date_pulled
  month_dir = f"{today:%m}-{today:%B}"  # 01-January

  company_slug = safe_slug(post.company) if post.company.strip() else "UNKNOWN_COMPANY"
  day_dir = f"{today:%d}-{company_slug}"

  out_dir = base_out_root / month_dir / day_dir
  out_dir.mkdir(parents=True, exist_ok=True)
  return out_dir


def _enforce_required_no_prompt(post: JobPost) -> None:
  missing: list[str] = []
  if not (post.company or "").strip():
    missing.append("company")
  if not (post.title or "").strip():
    missing.append("title")

  if missing:
    raise MissingRequiredFieldsError(missing, source=post.source, url=post.url)


def build_job_post_from_cli(args, cfg) -> JobPostBuildResult:
  # 1) capture
  if args.job_url and args.job_text:
    url = args.job_url.strip()
    job_text = Path(args.job_text).read_text(encoding="utf-8")
    capture_method = "args"
  else:
    cap = capture_from_clipboard()
    url = (cap.url or "").strip()
    job_text = (cap.description or "")
    capture_method = "clipboard"

  # 2) parse
  if is_linkedin_url(url):
    post = parse_linkedin_job_post(url=url, full_text=job_text)
  else:
    post = JobPost(
      url=url,
      source="other",
      date_pulled=date.today(),
      title="",
      company="",
      description=job_text.strip(),
      attributes={},
    )

  post.attributes.setdefault("capture_method", capture_method)

  # 3) enforce required (no prompting in core flow)
  _enforce_required_no_prompt(post)

  # 4) compute stopwords delta (do NOT mutate cfg here)
  stopwords_delta = company_stopwords(post.company)

  # 5) output dir
  base_out_root = Path(args.out_dir) if args.out_dir else Path(cfg.paths_out_root)
  out_dir = _compute_out_dir(base_out_root=base_out_root, post=post)

  # 6) write jobpost
  if not args.dry_run:
    jobpost_path = write_jobpost(out_dir, post)
  else:
    jobpost_path = out_dir / "DRY_RUN_jobpost.md"

  return JobPostBuildResult(
    post=post,
    out_dir=out_dir,
    jobpost_path=jobpost_path,
    stopwords_delta=stopwords_delta,
  )

def company_stopwords(company: str) -> set[str]:
  """
  Turn a company name into stopwords:
  - individual words
  - normalized variants
  """
  company = company.lower()

  # Split on spaces & punctuation
  parts = re.split(r"[^a-z0-9]+", company)

  out = set(p for p in parts if len(p) >= 3)

  # Add full company name as a phrase
  if company.strip():
    out.add(company.strip())

  return out