# it focuses on what you is mandatory (title, company) and stores any extra “attributes” opportunistically.

from datetime import date

from .types import JobPost


def parse_linkedin_job_post(*, url: str, full_text: str) -> JobPost:
  """
  Best-effort parse from a LinkedIn job post copy-paste blob.

  Guarantees:
    - returns JobPost with description=full_text
    - title/company may be empty => caller must enforce via prompt
  """
  text = full_text.strip()

  # Split around "About the job" if present (common pattern)
  before_about, sep, after_about = text.partition("About the job")

  header = before_about.strip()
  description = text

  # Try to extract company/title from early lines.
  # Typical copy has company/title near the top but formats vary.
  header_lines = [ln.strip() for ln in header.splitlines() if ln.strip()]

  company = ""
  title = ""

  # Heuristic: if first two non-empty lines exist, treat them as company/title,
  # but only if they look reasonable (not "Share", "Show more options", etc.) or contain "company logo"
  DUMB_EXACT = {
      "share",
      "show more options",
  }

  DUMB_CONTAINS = {
      "company logo",
  }

  cleaned = []
  for ln in header_lines:
      ln_low = ln.lower()
      if ln_low in DUMB_EXACT:
          continue
      if any(substr in ln_low for substr in DUMB_CONTAINS):
          continue
      cleaned.append(ln)

  if len(cleaned) >= 2:
    # Many pastes are: COMPANY on first line, TITLE on second
    company = cleaned[0]
    title = cleaned[1]
  elif len(cleaned) == 1:
    # Could be title-only or company-only; leave enforcement to caller
    title = cleaned[0]

  attributes: dict[str, str] = {}

  # Optional: try to capture location / workplace type / employment type if present
  # Common dot-separated segment "City, State · Remote · Full-time"
  dot_segments = []
  for ln in cleaned[:6]:
    if " · " in ln:
      dot_segments.extend([x.strip() for x in ln.split(" · ") if x.strip()])

  # naive mapping attempt
  for seg in dot_segments:
    low = seg.lower()
    if "remote" in low or "hybrid" in low or "on-site" in low or "onsite" in low:
      attributes["workplace_type"] = seg
    elif "full-time" in low or "part-time" in low or "contract" in low or "temporary" in low:
      attributes["employment_type"] = seg
    elif "," in seg and len(seg) <= 60:
      attributes.setdefault("location", seg)

  return JobPost(
    url=url.strip(),
    source="linkedin",
    date_pulled=date.today(),
    title=title,
    company=company,
    description=description,
    attributes=attributes,
  )
