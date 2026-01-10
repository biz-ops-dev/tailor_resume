from __future__ import annotations


def strip_notes_from_markdown(md: str) -> str:
  lines = md.splitlines()
  out: list[str] = []
  in_summary = False

  def is_h2(line: str) -> bool:
    return line.startswith("## ")

  for line in lines:
    s = line.strip()

    if is_h2(line):
      section = line[3:].strip().lower()
      in_summary = (section == "summary")
      out.append(line)
      continue

    if (not in_summary) and s.startswith("<!--"):
      continue

    if (not in_summary) and s.startswith(">"):
      continue

    out.append(line)

  return "\n".join(out).rstrip() + "\n"


def validate_notes_placement(md: str) -> list[str]:
  lines = md.splitlines()
  errors: list[str] = []
  in_summary = False

  def is_h2(line: str) -> bool:
    return line.startswith("## ")

  def is_bullet(line: str) -> bool:
    return line.startswith("- ") or line.startswith("* ")

  def is_blockquote(line: str) -> bool:
    return line.lstrip().startswith(">")

  def is_html_comment(line: str) -> bool:
    return line.lstrip().startswith("<!--")

  for i, line in enumerate(lines):
    if is_h2(line):
      section = line[3:].strip().lower()
      in_summary = (section == "summary")
      continue

    if in_summary:
      continue

    if is_blockquote(line):
      j = i - 1
      blanks = 0
      while j >= 0 and lines[j].strip() == "":
        blanks += 1
        j -= 1
      if blanks > 1:
        errors.append(f"Line {i+1}: blockquote is separated from bullet by >1 blank line.")
      if j < 0 or not is_bullet(lines[j]):
        errors.append(f"Line {i+1}: blockquote must follow a bullet ('- ' or '* ').")
      continue

    if is_html_comment(line):
      errors.append(f"Line {i+1}: HTML comment found outside SUMMARY (did stripping run?).")

  return errors
