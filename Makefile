DB ?= data/kg.sqlite
EXPORT ?= $(HOME)/Downloads

.PHONY: help install test lint build pyz status serve web ui sync check clean

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n",$$1,$$2}'

install:  ## editable install with dev extras, into .venv (bare pip is refused on modern system Python)
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	@echo "  activate with:  source .venv/bin/activate"

test:  ## run the suite (no large fixtures needed)
	pytest -q

lint:  ## ruff
	ruff check src tests

build:  ## build a mirror   make build EXPORT=~/Downloads
	learning-net build $(EXPORT) --db $(DB)

pyz:  ## single-file build, runs on stock Python: python3 dist/learning-net.pyz init
	rm -rf build/pyz
	mkdir -p build/pyz dist
	cp -R src/learningnet build/pyz/learningnet
	find build/pyz -name '__pycache__' -type d -exec rm -rf {} +
	python3 -m zipapp build/pyz -m "learningnet.cli:main" \
		-o dist/learning-net.pyz -p "/usr/bin/env python3" --compress
	@echo "  dist/learning-net.pyz — no pip, no venv:  python3 learning-net.pyz init"

sync:  ## diff an export against the mirror, rebuild if safe
	learning-net sync $(EXPORT) --db $(DB)

check:  ## report drift only, never rebuild (use in CI)
	learning-net sync $(EXPORT) --db $(DB) --check

status:  ## what is in the mirror and how stale it is
	learning-net status --db $(DB)

serve:  ## MCP server on stdio
	learning-net serve --db $(DB)

web:  ## web explorer UI   make web DB=data/kg.sqlite
	learning-net web --db $(DB) --open

ui:  ## rebuild the web bundle into the package (Node needed here, and only here)
	cd web && npm install && npm run build

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
