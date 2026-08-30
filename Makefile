PYTHON ?= python3.11
ARGS ?= --generations 5

.PHONY: setup loop api ui ui-build test lint calibrate twin atlas eval-honest clean test-llm

setup:
	@command -v uv >/dev/null && uv venv --python $$(command -v $(PYTHON) || command -v python3) .venv && \
		uv pip install --python .venv/bin/python -e ".[dev]" || \
		{ $(PYTHON) -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -e ".[dev]"; }

loop:
	.venv/bin/python -m agni.loop.redqueen $(ARGS)

atlas:
	.venv/bin/python -m agni.genome.atlas

eval-honest:
	.venv/bin/python scripts/eval_honest.py

calibrate twin:
	.venv/bin/python -m agni.twin.calibrate

api:
	.venv/bin/uvicorn agni.server.main:app --reload --port 8000

ui:
	cd web && npm run dev

ui-build:
	cd web && npm ci && npm run build

test-llm:
	.venv/bin/python scripts/test_llm.py

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check agni tests

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__ runs/*.json
