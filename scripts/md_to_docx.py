#!/usr/bin/env python3

"""" 

assumes Markdown is already final
does no content mutation
only converts + opens

how to run from command line

python3 -m tailor_resume \
  --resume /path/to/final_resume.md \
  --out-dir out

"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

# --------------------------------------------------
# CONFIG — hard-coded reference DOCX
# --------------------------------------------------
#REFERENCE_DOCX = Path(__file__).resolve().parent / "assets" / "reference_resume.docx"

REFERENCE_DOCX = Path("/Users/alexandercarnevale/my_repos/tailor_resume/assets/reference_resume.docx")


def md_to_docx(md_path: Path) -> Path:
  if not md_path.exists():
    raise FileNotFoundError(f"Input file not found: {md_path}")

  if md_path.suffix.lower() != ".md":
    raise ValueError(f"Expected a .md file, got: {md_path.name}")

  if not REFERENCE_DOCX.exists():
    raise FileNotFoundError(f"Reference DOCX not found: {REFERENCE_DOCX}")

  out = md_path.with_suffix(".docx")

  cmd = [
    "pandoc",
    str(md_path),
    f"--reference-doc={REFERENCE_DOCX}",
    "-o",
    str(out),
  ]

  subprocess.run(cmd, check=True)

  # macOS: open the file in the default application (Word)
  subprocess.run(["open", str(out)], check=False)

  return out


def main() -> int:
  ap = argparse.ArgumentParser(
    description="Convert Markdown file to DOCX using Pandoc and open it"
  )
  ap.add_argument(
    "input",
    type=Path,
    help="Path to the input .md file"
  )

  args = ap.parse_args()

  out = md_to_docx(args.input)
  print(f"Created and opened: {out}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())