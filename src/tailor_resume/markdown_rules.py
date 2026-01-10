from __future__ import annotations


def normalize_markdown_spacing(md: str) -> str:
  lines = md.splitlines()
  out: list[str] = []

  def is_any_header(s: str) -> bool:
    return s.startswith("#")

  def is_bullet(s: str) -> bool:
    return s.startswith("- ")

  # Pass 1: remove blank lines between bullets (tight lists)
  i = 0
  while i < len(lines):
    out.append(lines[i])
    if is_bullet(lines[i]):
      j = i + 1
      while j < len(lines) and lines[j] == "":
        k = j
        while k < len(lines) and lines[k] == "":
          k += 1
        if k < len(lines) and is_bullet(lines[k]):
          j = k
          continue
        break
      i = j
    else:
      i += 1

  lines = out
  out = []

  # Pass 2: enforce header boundaries + collapse extra blanks
  prev_blank = False
  for line in lines:
    if is_any_header(line) and out:
      if out[-1] != "":
        out.append("")

    if is_any_header(line) and out and out[-1].startswith("- "):
      out.append("")

    if line == "":
      if prev_blank:
        continue
      prev_blank = True
      out.append("")
      continue

    prev_blank = False
    out.append(line)

  while out and out[-1] == "":
    out.pop()

  return "\n".join(out).rstrip() + "\n"


def validate_markdown(md: str) -> list[str]:
  lines = md.splitlines()
  errors: list[str] = []

  def is_header(s: str) -> bool:
    return s.startswith("#")

  def is_bullet(s: str) -> bool:
    return s.startswith("- ")

  for i in range(len(lines) - 1):
    a = lines[i]
    b = lines[i + 1]

    if is_bullet(a) and is_header(b):
      errors.append(f"Line {i+1}: bullet immediately followed by header: {a!r} -> {b!r}")

    if a == "" and b == "":
      errors.append(f"Line {i+1}: multiple consecutive blank lines")

  return errors
