PY ?= python
RESUME ?= resume_base.md
OUTDIR ?= outputs
LOGCSV ?= logs/resume_runs.csv
PROFILE ?= base
STATUS ?=
USE_NLTK ?= 0


# Usage:
#   make tailor JOB=jobs/2025-12-30_senior_project_manager_acme.txt
tailor:
	@if [ -z "$(JOB)" ]; then echo "ERROR: provide JOB=path/to/job.txt"; exit 1; fi
	$(PY) tailor_resume.py \
	  --resume "$(RESUME)" \
	  --job "$(JOB)" \
	  --out-dir "$(OUTDIR)" \
	  --log-csv "$(LOGCSV)" \
	  --profile "$(PROFILE)" \
	  --status "$(STATUS)" \
	  $(if $(filter 1,$(USE_NLTK)),--use-nltk,)

# Convenience: list last 10 runs
tailor-log:
	@tail -n 10 "$(LOGCSV)" || true
