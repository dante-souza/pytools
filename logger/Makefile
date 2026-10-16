# Portable standalone Python logger demonstration (GNU Make).
# All terminal workflows have make targets; Python is an implementation detail.
.DEFAULT_GOAL := help
PYTHON ?= python
COLOR ?= always
FILE ?= examples/events.jsonl
PRETTY ?= 0
KIND ?= auto
HEADINGS ?= 1
PRETTY_FLAG = $(if $(filter 1 true yes on,$(PRETTY)),--pretty,)
HEADINGS_FLAG = $(if $(filter 0 false no off,$(HEADINGS)),--no-headings,)

.PHONY: help doctor demo smoke test check view pretty view-plain sample logger-demo integration-demo setup setup-notebook notebook clean

help:
	@echo "=== logger_general: standalone JSON + logs + notebook ==="
	@echo "make doctor                          - Python/package check"
	@echo "make demo COLOR=always               - Live runtime demo, no network"
	@echo "make smoke COLOR=always              - Runtime invariant checks in main()"
	@echo "make test                            - Complete offline unittest suite"
	@echo "make check                           - Smoke + unit tests"
	@echo "make pretty FILE=examples/events.jsonl COLOR=always"
	@echo "make view FILE=examples/events.jsonl PRETTY=0 COLOR=never"
	@echo "make view FILE=examples/event.json KIND=json PRETTY=1"
	@echo "make view-plain FILE=examples/events.jsonl - No ANSI"
	@echo "make sample                          - Generate example output in examples/output/"
	@echo "make integration-demo                - Embed the module in a fake application"
	@echo "make setup                           - Editable install (optional)"
	@echo "make setup-notebook                  - Install optional Jupyter dependencies"
	@echo "make notebook                        - Open notebook with Jupyter"
	@echo "make clean                           - Remove generated caches and example output"

doctor:
	$(PYTHON) --version
	$(PYTHON) -c "import logger_general; print('module:', logger_general.__file__); print('version:', logger_general.__version__)"

demo:
	$(PYTHON) -m logger_general demo --color "$(COLOR)"

smoke:
	$(PYTHON) -m logger_general selftest --color "$(COLOR)"

test:
	$(PYTHON) -m unittest discover -s tests -v

check: smoke test

view:
	$(PYTHON) -m logger_general view "$(FILE)" --kind "$(KIND)" $(PRETTY_FLAG) $(HEADINGS_FLAG) --color "$(COLOR)"

pretty: PRETTY=1
pretty: view

view-plain: COLOR=never
view-plain: pretty

# No third-party libraries or network calls necessary.
sample:
	$(PYTHON) -m examples.integration_example --generate-only

integration-demo:
	$(PYTHON) -m examples.integration_example --color "$(COLOR)"

logger-demo: demo

setup:
	$(PYTHON) -m pip install -e .

setup-notebook:
	$(PYTHON) -m pip install notebook ipykernel

notebook:
	$(PYTHON) -m notebook notebooks/logger_general_exemplos.ipynb

clean:
	$(PYTHON) -m examples.cleanup
