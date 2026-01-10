Tailor Resume
=============

Tailor Resume is a CLI tool that takes a base resume template and a job posting,
then produces a tailored resume and a structured report explaining what changed.

The system is designed for iterative learning:
you can refine scoring, structure, and content over time without rewriting the pipeline.


Mental Model
------------

Think of Tailor Resume as a **three-stage pipeline**:

1. Capture
2. Transform
3. Export


1) Capture
----------

Inputs:
- A base resume template (Markdown)
- A job posting (clipboard or file)
- Configuration (TOML + YAML)

Responsibilities:
- Capture job URL and description
- Parse job metadata (LinkedIn or generic)
- Enforce required fields (job title, company)
- Load configuration and stopwords

Important principle:
The base resume is a TEMPLATE, not your real resume.
It may contain placeholders such as:

  YOUR_NAME_HERE
  {{CONTACT_LINE}}

Those placeholders must be resolved before export.


2) Transform
------------

This is the core logic of the system.

Responsibilities:
- Parse the resume into structured sections
- Score bullets against the job description
- Retain, drop, or promote bullets per role
- Apply guardrails (e.g., migrations must appear if job mentions them)
- Reorder CORE COMPETENCIES based on relevance
- Inject contact information
- Add resume-specific YAML frontmatter

Key principles:
- JobPost.title remains the canonical job title in code
- YAML frontmatter uses job_title for clarity
- All transformations are deterministic and reproducible
- Config controls behavior; CLI flags override only when necessary


3) Export
---------

Outputs:
- Job post Markdown (archival)
- Tailored resume Markdown
- JSON report explaining scoring and decisions
- Optional CSV run log
- Optional DOCX export via Pandoc

Important principle:
Export scripts (Pandoc, DOCX) do NOT mutate content.
They assume the Markdown is already final.


Directory Structure
-------------------

Outputs are organized automatically:

out/
  01-January/
    09-Acme Corp/
      YYYY-MM-DD_jobpost_acme_corp.md
      YYYY-MM-DD_resume_acme_corp_service_manager.md
      YYYY-MM-DD_report_acme_corp_service_manager.json

The output root and CSV log path are defined in config, not hardcoded.


Configuration
-------------

Configuration lives in tailor_resume.toml and supporting YAML files.

Examples:
- Contact information (mandatory)
- Output root directory
- CSV log location
- Scoring weights
- Guardrails
- Stopwords (global + per-company)

Stopwords are split intentionally:
- Global stopwords live in stopwords.yaml
- Company-specific stopwords are added per run


What This Tool Is (and Is Not)
------------------------------

This tool IS:
- A resume tailoring engine
- A learning platform for resume optimization
- A deterministic system you can refactor safely

This tool is NOT:
- A GUI application
- A one-click resume generator
- A final product (it is meant to evolve)


Typical Usage
-------------

1. Edit the base resume template
2. Run the CLI to capture a job posting
3. Review the tailored Markdown
4. Review the JSON report
5. Export to DOCX if needed


Philosophy
----------

This project prioritizes:
- Clarity over cleverness
- Explicitness over magic
- Config over hardcoding
- Reproducibility over convenience

Refactors are expected.
Learning is expected.
V1 is intentionally conservative.
