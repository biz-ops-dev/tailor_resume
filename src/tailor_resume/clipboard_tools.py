# clipboard_tools.py
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable


class ClipboardError(RuntimeError):
  pass


@dataclass(frozen=True)
class ClipboardBackend:
  name: str
  paste_cmd: list[str]
  copy_cmd: list[str]


def _detect_backend() -> ClipboardBackend:
  """
  Detect a working clipboard backend.
  macOS: pbpaste/pbcopy
  Linux: xclip or xsel
  """
  if shutil.which("pbpaste") and shutil.which("pbcopy"):
    return ClipboardBackend(
      name="macos-pbcopy",
      paste_cmd=["pbpaste"],
      copy_cmd=["pbcopy"],
    )

  if shutil.which("xclip"):
    return ClipboardBackend(
      name="linux-xclip",
      paste_cmd=["xclip", "-selection", "clipboard", "-o"],
      copy_cmd=["xclip", "-selection", "clipboard"],
    )

  if shutil.which("xsel"):
    return ClipboardBackend(
      name="linux-xsel",
      paste_cmd=["xsel", "--clipboard", "--output"],
      copy_cmd=["xsel", "--clipboard", "--input"],
    )

  raise ClipboardError("No clipboard tool found (pbpaste/pbcopy, xclip, or xsel).")


def get_clipboard(*, backend: ClipboardBackend | None = None) -> str:
  """Return current clipboard contents as text (UTF-8)."""
  b = backend or _detect_backend()
  result = subprocess.run(b.paste_cmd, capture_output=True, text=True)
  if result.returncode != 0:
    raise ClipboardError(
      f"Clipboard paste failed using {b.name}: {result.stderr.strip()}"
    )
  return result.stdout


def copy_to_clipboard(text: str, *, backend: ClipboardBackend | None = None) -> None:
  """Copy text to system clipboard (UTF-8)."""
  b = backend or _detect_backend()
  # Use text=True so we can pass a str directly (avoid manual encoding mistakes).
  result = subprocess.run(b.copy_cmd, input=text, text=True, capture_output=True)
  if result.returncode != 0:
    raise ClipboardError(
      f"Clipboard copy failed using {b.name}: {result.stderr.strip()}"
    )


def clear_clipboard(*, backend: ClipboardBackend | None = None) -> None:
  """Clear clipboard contents."""
  copy_to_clipboard("", backend=backend)


def wait_for_clipboard_change(
  *,
  prompt: str | None = None,
  clear_first: bool = False,
  poll_seconds: float = 0.15,
  timeout_seconds: float | None = None,
  require_nonempty: bool = False,
  backend: ClipboardBackend | None = None,
) -> str:
  """
  Wait until clipboard content changes, then return the new content.

  - clear_first=True implements your "capture next item to clipboard" behavior.
  - timeout_seconds prevents hanging forever (None = wait forever).
  - require_nonempty=True ignores changes that are empty/whitespace.
  """
  b = backend or _detect_backend()

  if clear_first:
    clear_clipboard(backend=b)

  if prompt:
    print(prompt)

  start = time.monotonic()
  last = get_clipboard(backend=b)

  while True:
    if timeout_seconds is not None:
      elapsed = time.monotonic() - start
      if elapsed >= timeout_seconds:
        raise TimeoutError("Timed out waiting for clipboard change.")

    current = get_clipboard(backend=b)
    if current != last:
      if require_nonempty and not current.strip():
        last = current
      else:
        return current

    time.sleep(poll_seconds)


def log_transform(
  inp: str,
  out: str,
  *,
  log_path: str = "clipboard_cleaner.log",
  note: str | None = None,
) -> None:
  """Append input/output pair with timestamp to a log file."""
  ts = datetime.now().isoformat(timespec="seconds")
  with open(log_path, "a", encoding="utf-8") as f:
    f.write(f"--- {ts} ---\n")
    if note:
      f.write(f"NOTE: {note}\n")
    f.write("INPUT:\n")
    f.write(inp)
    f.write("\n\nOUTPUT:\n")
    f.write(out)
    f.write("\n\n")


# ---- Optional: a small pipeline helper (useful once you wire CLI flags) ----

Transform = Callable[[str], str]


def run_pipeline(text: str, transforms: Iterable[Transform]) -> str:
  """
  Apply transforms in order. Keep this tiny; your other scripts can provide
  the actual transform functions (remove whitespace, vocab capture, clean_line, etc.).
  """
  out = text
  for fn in transforms:
    out = fn(out)
  return out


def fatal(msg: str, *, code: int = 1) -> "NoReturn":
  sys.stderr.write(msg.rstrip() + "\n")
  raise SystemExit(code)