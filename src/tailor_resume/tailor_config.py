from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ----------------------------
# TOML loading (py3.11+ tomllib, fallback to tomli if installed)
# ----------------------------
try:
  import tomllib  # py3.11+
except Exception:  # pragma: no cover
  tomllib = None  # type: ignore[assignment]
  try:
    import tomli as tomllib  # type: ignore[assignment]
  except Exception:
    tomllib = None  # type: ignore[assignment]

# Should be in tailor_config?
paths_out_root: str = "out"
paths_csv_log: str = "out/run_log.csv"


DEFAULT_ACTION_VERBS = {
  "led","lead","owned","own","built","build","created","create","implemented","implement","launched","launch",
  "designed","design","delivered","deliver","migrated","migrate","optimized","optimize","scaled","scale",
  "spearheaded","drove","drive","managed","manage","guided","guide","partnered","partner","facilitated","facilitate",
  "oversaw","oversee","standardized","standardize","developed","develop","improved","improve","aligned","align"
}

DEFAULT_GENERIC_PENALTIES = {
  "responsible for",
  "worked on",
  "helped",
  "assisted",
  "involved in",
  "participated in",
  "contributed to",
}


@dataclass
class TailorConfig:
  # behavior
  use_nltk: bool = False

  # bullet retention
  per_role_keep: int = 6
  min_per_role_keep: int = 3
  drop_below_score: float = 0.0

  # scoring weights
  w_required: float = 3.0
  w_nice: float = 1.0
  w_domain: float = 2.0
  w_overlap: float = 0.12
  w_phrase_hit: float = 1.25
  w_metric: float = 1.5
  w_action_verb: float = 0.75
  w_generic_penalty: float = 1.0
  w_length_penalty: float = 0.4

  # keyword sources (optional)
  required_terms: list[str] = field(default_factory=list)
  nice_to_have_terms: list[str] = field(default_factory=list)
  domain_terms: list[str] = field(default_factory=list)

  # contact information
  contact_email: str = ""
  contact_location: str = ""
  contact_phone: str = ""

  # extraction
  max_auto_terms: int = 25
  ##below line replaced when went to yaml file for stopwords
  #stopwords: set[str] = field(default_factory=lambda: set(DEFAULT_STOPWORDS))
  stopwords: set[str] = field(default_factory=set)

  action_verbs: set[str] = field(default_factory=lambda: set(DEFAULT_ACTION_VERBS))
  generic_penalties: set[str] = field(default_factory=lambda: set(DEFAULT_GENERIC_PENALTIES))

  # guardrails: keep at least one bullet matching certain themes if the job mentions them
  guardrails: list[dict] = field(default_factory=lambda: [
    {
      "name": "migration",
      "triggers": ["migration", "migrate", "data migration", "platform migration", "system migration", "transition", "cutover"],
      "must_keep_phrases": ["migration", "migrate", "data migration", "platform", "transition", "cutover"],
      "min_keep": 1,
    },
  ])

  


def load_config(path: Path | None) -> TailorConfig:
  cfg = TailorConfig()

  # If no config path provided, return defaults (caller may enforce required fields).
  if path is None:
    return cfg

  if not path.exists():
    raise FileNotFoundError(f"Config not found: {path}")

  if tomllib is None:
    raise RuntimeError("TOML parser not available. Use Python 3.11+ (tomllib) or install tomli.")

  data = tomllib.loads(path.read_text(encoding="utf-8")) or {}

  # top-level flags
  cfg.use_nltk = bool(data.get("use_nltk", cfg.use_nltk))

  # sections
  tailor = data.get("tailor") or {}
  scoring = data.get("scoring") or {}
  terms = data.get("terms") or {}
  contact = data.get("contact") or {}
  paths = data.get("paths") or {}

  # tailor behavior
  cfg.per_role_keep = int(tailor.get("per_role_keep", cfg.per_role_keep))
  cfg.min_per_role_keep = int(tailor.get("min_per_role_keep", cfg.min_per_role_keep))
  cfg.drop_below_score = float(tailor.get("drop_below_score", cfg.drop_below_score))

  # scoring weights
  cfg.w_required = float(scoring.get("w_required", cfg.w_required))
  cfg.w_nice = float(scoring.get("w_nice", cfg.w_nice))
  cfg.w_domain = float(scoring.get("w_domain", cfg.w_domain))
  cfg.w_overlap = float(scoring.get("w_overlap", cfg.w_overlap))
  cfg.w_phrase_hit = float(scoring.get("w_phrase_hit", cfg.w_phrase_hit))
  cfg.w_metric = float(scoring.get("w_metric", cfg.w_metric))
  cfg.w_action_verb = float(scoring.get("w_action_verb", cfg.w_action_verb))
  cfg.w_generic_penalty = float(scoring.get("w_generic_penalty", cfg.w_generic_penalty))
  cfg.w_length_penalty = float(scoring.get("w_length_penalty", cfg.w_length_penalty))

  # terms
  cfg.required_terms = list(terms.get("required", cfg.required_terms))
  cfg.nice_to_have_terms = list(terms.get("nice_to_have", cfg.nice_to_have_terms))
  cfg.domain_terms = list(terms.get("domain", cfg.domain_terms))
  cfg.max_auto_terms = int(terms.get("max_auto_terms", cfg.max_auto_terms))

  # optional keyword sources (still supported, even if you now prefer stopwords.yaml)
  if "stopwords" in data:
    cfg.stopwords = set(data["stopwords"])
  if "action_verbs" in data:
    cfg.action_verbs = set(data["action_verbs"])
  if "generic_penalties" in data:
    cfg.generic_penalties = set(data["generic_penalties"])

  # guardrails
  guardrails = data.get("guardrails")
  if isinstance(guardrails, list):
    cfg.guardrails = []
    for g in guardrails:
      if not isinstance(g, dict):
        continue
      cfg.guardrails.append({
        "name": g.get("name", "unnamed"),
        "triggers": list(g.get("triggers", [])),
        "must_keep_phrases": list(g.get("must_keep_phrases", [])),
        "min_keep": int(g.get("min_keep", 1)),
      })

  # contact (mandatory enforced in cli.py)
  if isinstance(contact, dict):
    cfg.contact_email = str(contact.get("email", cfg.contact_email))
    cfg.contact_location = str(contact.get("location", cfg.contact_location))
    cfg.contact_phone = str(contact.get("phone", cfg.contact_phone))

  # paths (NEW: define out root + csv log default in config)
  # Requires TailorConfig to have: paths_out_root, paths_csv_log (strings)
  if isinstance(paths, dict):
    if "out_root" in paths:
      cfg.paths_out_root = str(paths.get("out_root") or cfg.paths_out_root)
    if "csv_log" in paths:
      cfg.paths_csv_log = str(paths.get("csv_log") or cfg.paths_csv_log)

  return cfg

