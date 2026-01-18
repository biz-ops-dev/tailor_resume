# jobpost_types.py


"""imports nothing from your pipeline
imports nothing from IO
is safe to import everywhere
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date

@dataclass
class JobPost:
  url: str
  source: str
  date_pulled: date
  title: str
  company: str
  description: str
  attributes: dict[str, str] = field(default_factory=dict)
