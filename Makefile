VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
PYTEST=$(VENV)/bin/pytest

.PHONY: help setup install test cov run run-http clean

help:
	@echo "Targets: setup, install, test, cov, run, run-http, clean"

$(VENV):
	python3 -m venv $(VENV)

install: $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r promptyoself/requirements.txt

setup: install
	@echo "Environment ready. Activate with: source $(VENV)/bin/activate"

test:
	$(PYTEST)

cov:
	$(PYTEST) --cov=promptyoself_mcp_server --cov=promptyoself --cov-report=term-missing

run:
	$(PY) promptyoself_mcp_server.py

run-http:
	$(PY) promptyoself_mcp_server.py --transport http --host 127.0.0.1 --port 8000 --path /mcp

clean:
	rm -rf $(VENV) .pytest_cache .coverage htmlcov artifacts/coverage artifacts/coverage-final
