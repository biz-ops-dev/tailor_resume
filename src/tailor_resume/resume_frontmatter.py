from __future__ import annotations

from datetime import date


def _yaml_quote(s: str) -> str:
  s = (s or "").replace('"', '\\"')
  return f'"{s}"'


def render_resume_frontmatter(
  *,
  job_title: str,
  company: str,
  date_pulled: date,
  source: str,
  url: str,
  profile: str,
) -> str:
  lines: list[str] = []
  lines.append("---")
  lines.append(f"job_title: {_yaml_quote(job_title)}")
  lines.append(f"company: {_yaml_quote(company)}")
  lines.append(f"date_pulled: {_yaml_quote(date_pulled.isoformat())}")
  lines.append(f"source: {_yaml_quote(source)}")
  lines.append(f"url: {_yaml_quote(url)}")
  lines.append(f"profile: {_yaml_quote(profile)}")
  lines.append("---")
  lines.append("")
  return "\n".join(lines)
