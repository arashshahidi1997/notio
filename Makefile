# ---- notio ------------------------------------------------------------------

PYTHON ?= /storage/share/python/environments/Anaconda3/envs/labpy/bin/python

include workflow/docs.mk
include workflow/notes.mk

.PHONY: help init
help:
	@echo "Usage:"
	@echo "  make init                  Scaffold .notio/templates and indexes"
	@echo "  make note-daily            Create/update a daily note"
	@echo "  make note-weekly           Create/update a weekly note"
	@echo "  make note-<type>           Create an event note"
	@echo "  make toc-<type>            Regenerate one index"
	@echo "  make toc-all               Regenerate all indexes"
	@echo ""
	@echo "Overrides:"
	@echo "  DATE=YYYY-MM-DD"
	@echo "  OWNER=<name>"
	@echo "  TITLE='...'"

init:
	@PYTHONPATH=src $(PYTHON) -m notio --root . init
