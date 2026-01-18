from __future__ import annotations

from .models import ResumeDoc, Role


def parse_professional_experience(md_text: str) -> ResumeDoc:
  """return a resume document

  Args:
      md_text (str): base resume

  Returns:
      ResumeDoc: dataclass with lines and roles
  """
  lines = md_text.splitlines(keepends=False)
  doc = ResumeDoc(lines=list(lines))

  # below are "markers" not triggers
  professional_experience_start = None
  professional_experience_end = None

  for i, line in enumerate(lines):
    if line.startswith("## "):
      section_header = line[3:].strip().lower()
      if section_header == "professional_experience":
        professional_experience_start = i # set to the index of the header line
        # skips rest of this loop iteration but arsing continues through subsequent lines
        continue 

      # Detecting the next section header
      # works because of line "if line.startswith("## "):"
      # The first new section header after professional_experience triggers the end
      if professional_experience_start is not None and i > professional_experience_start:
        professional_experience_end = i
        break

  doc.prof_exp_start_idx = professional_experience_start

  #Save the end index, but only if a start was found
  doc.prof_exp_end_idx = professional_experience_end if professional_experience_start is not None else None

  # bail early
  # future - error
  if professional_experience_start is None:
    return doc

  # Compute a usable end for slicing
  ## If you found an end header (“## education” etc.), slice up to that.
  ## Otherwise, assume the section goes to the end of the document.
  end = professional_experience_end if professional_experience_end is not None else len(lines)

  # Slice out the professional_experience_block
  professional_experience_block = lines[professional_experience_start:end]

  roles: list[Role] = []
  current: Role | None = None

  for line in professional_experience_block:
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