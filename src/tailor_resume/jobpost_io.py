# Creates yyyy-mm-dd_company_title.md with YAML frontmatter.
from datetime import date
from pathlib import Path

from .models import JobPost
from .text_utils import safe_slug


def _yaml_escape(s: str) -> str:
  # simple YAML-safe quoting
  s = (s or "").replace('"', '\\"')
  return f'"{s}"'


def jobpost_filename(post: JobPost) -> str:
  d = post.date_pulled.strftime("%Y-%m-%d")
  company = safe_slug(post.company)
  title = safe_slug(post.title)
  return f"{d}_{company}_{title}.md"


def render_jobpost_markdown(post: JobPost) -> str:
  lines: list[str] = []
  lines.append("---")
  lines.append(f"title: {_yaml_escape(post.title)}")
  lines.append(f"company: {_yaml_escape(post.company)}")
  lines.append(f"date_pulled: {_yaml_escape(post.date_pulled.isoformat())}")
  lines.append(f"source: {_yaml_escape(post.source)}")
  lines.append(f"url: {_yaml_escape(post.url)}")

  if post.attributes:
    lines.append("attributes:")
    for k in sorted(post.attributes.keys()):
      v = post.attributes[k]
      if v is None:
        continue
      lines.append(f"  {k}: {_yaml_escape(str(v))}")

  lines.append("---")
  lines.append("")
  lines.append("# Job Post")
  lines.append("")
  lines.append(post.description.rstrip())
  lines.append("")
  return "\n".join(lines)


def write_jobpost(out_dir: Path, post: JobPost) -> Path:
  out_dir.mkdir(parents=True, exist_ok=True)
  path = out_dir / jobpost_filename(post)
  path.write_text(render_jobpost_markdown(post), encoding="utf-8")
  return path
