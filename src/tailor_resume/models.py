from dataclasses import dataclass, field
from datetime import date


@dataclass
class Role:
  role_header: str
  company_header: str | None = None
  bullet_lines: list[str] = field(default_factory=list)
  other_lines: list[str] = field(default_factory=list)


@dataclass
class ResumeDoc:
  lines: list[str]
  prof_exp_start_idx: int | None = None
  prof_exp_end_idx: int | None = None
  roles: list[Role] = field(default_factory=list)



