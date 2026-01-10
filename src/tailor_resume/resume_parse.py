from __future__ import annotations

from .models import ResumeDoc, Role


def parse_resume(md_text: str) -> ResumeDoc:
  lines = md_text.splitlines(keepends=False)
  doc = ResumeDoc(lines=list(lines))

  prof_start = None
  prof_end = None
  for i, line in enumerate(lines):
    if line.startswith("## "):
      section = line[3:].strip().lower()
      if section == "professional_experience":
        prof_start = i
        continue
      if prof_start is not None and i > prof_start:
        prof_end = i
        break

  doc.prof_exp_start_idx = prof_start
  doc.prof_exp_end_idx = prof_end if prof_start is not None else None

  if prof_start is None:
    return doc

  end = prof_end if prof_end is not None else len(lines)
  block = lines[prof_start:end]

  roles: list[Role] = []
  current: Role | None = None

  for line in block:
    if line.startswith("### "):
      if current is not None:
        roles.append(current)
      current = Role(role_header=line)
      continue

    if current is None:
      continue

    if line.startswith("#### "):
      current.company_header = line
      continue

    if line.startswith("- "):
      current.bullet_lines.append(line)
      continue

    current.other_lines.append(line)

  if current is not None:
    roles.append(current)

  doc.roles = roles
  return doc


def render_resume_with_new_roles(doc: ResumeDoc, new_roles: list[Role]) -> str:
  if doc.prof_exp_start_idx is None:
    return "\n".join(doc.lines).rstrip() + "\n"

  start = doc.prof_exp_start_idx
  end = doc.prof_exp_end_idx if doc.prof_exp_end_idx is not None else len(doc.lines)

  out_lines: list[str] = []
  out_lines.extend(doc.lines[:start])

  orig_block = doc.lines[start:end]
  out_lines.append(orig_block[0])  # "## PROFESSIONAL_EXPERIENCE"

  idx = 1
  while idx < len(orig_block) and not orig_block[idx].startswith("### "):
    out_lines.append(orig_block[idx])
    idx += 1

  for r in new_roles:
    out_lines.append(r.role_header)
    if r.company_header is not None:
      out_lines.append(r.company_header)

    for ln in r.other_lines:
      if ln.strip():
        out_lines.append(ln)

    for b in r.bullet_lines:
      out_lines.append(b)

    out_lines.append("")

  while out_lines and out_lines[-1] == "":
    out_lines.pop()

  out_lines.extend(doc.lines[end:])
  return "\n".join(out_lines).rstrip() + "\n"