from dataclasses import dataclass
from datetime import date
from .clipboard_tools import wait_for_clipboard_change


@dataclass(frozen=True)
class ClipboardCapture:
  url: str
  description: str


def capture_from_clipboard() -> ClipboardCapture:
  url = wait_for_clipboard_change(
    prompt="1) Copy the job posting URL to your clipboard now.",
    clear_first=True,
    require_nonempty=True,
  ).strip()

  desc = wait_for_clipboard_change(
    prompt="2) Copy the FULL job description text to your clipboard now.",
    clear_first=True,
    require_nonempty=True,
  ).strip()

  return ClipboardCapture(url=url, description=desc)



