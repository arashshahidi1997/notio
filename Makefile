# ---- notio ------------------------------------------------------------------

PYTHON ?= /storage/share/python/environments/Anaconda3/envs/labpy/bin/python
PYTEST_PYTHON ?= /storage/share/python/environments/Anaconda3/envs/labpy/bin/python
PUBLISH ?= /storage2/arash/infra/bin/publish_pypi.sh
DATALAD ?= /storage/share/python/environments/Anaconda3/envs/cogpy/bin/datalad

include workflow/docs.mk
include workflow/notes.mk

.PHONY: help init dev test docs docs-serve build check clean publish publish-test save push

help:
	@echo "Usage:"
	@echo "  make init                  Scaffold .notio/templates and indexes"
	@echo "  make note-daily            Create/update a daily note"
	@echo "  make note-weekly           Create/update a weekly note"
	@echo "  make note-<type>           Create an event note"
	@echo "  make toc-<type>            Regenerate one index"
	@echo "  make toc-all               Regenerate all indexes"
	@echo ""
	@echo "  make dev                   Install editable package with dev extras"
	@echo "  make test                  Run test suite"
	@echo "  make docs                  Build MkDocs site"
	@echo "  make docs-serve            Serve MkDocs locally"
	@echo "  make build                 Build wheel and sdist"
	@echo "  make check                 Run twine check on dist artifacts"
	@echo "  make clean                 Remove local build artifacts"
	@echo "  make publish               Publish to PyPI"
	@echo "  make publish-test          Publish to TestPyPI"
	@echo ""
	@echo "Overrides:"
	@echo "  DATE=YYYY-MM-DD"
	@echo "  OWNER=<name>"
	@echo "  TITLE='...'"

init:
	@PYTHONPATH=src $(PYTHON) -m notio --root . init

# ---- development ------------------------------------------------------------

dev:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	PYTHONPATH=src $(PYTEST_PYTHON) -m pytest

docs:
	$(PYTHON) -m mkdocs build --strict

docs-serve:
	$(PYTHON) -m mkdocs serve

# ---- packaging --------------------------------------------------------------

build:
	$(PYTHON) -m build

check:
	$(PYTHON) -m twine check dist/*

clean:
	rm -rf build/ dist/ site/ .pytest_cache/ .mypy_cache/
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

publish:
	$(PUBLISH)

publish-test:
	$(PUBLISH) --test

# ---- datalad ----------------------------------------------------------------

save:
	$(DATALAD) save -m "notio"

push:
	$(DATALAD) push --to github

-include .projio/projio.mk
