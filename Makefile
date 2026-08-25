PYTHON ?= python3.11
ARGS ?= --generations 5

.PHONY: setup loop api test lint calibrate clean

setup:
	@command -v uv >/dev/null && uv venv --python $$(command -v $(PYTHON) || command -v python3) .venv && \
		uv pip install --python .venv/bin/python -e ".[dev]" || \
		{ $(PYTHON) -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -e ".[dev]"; }

loop:
	.venv/bin/python -m agni.loop.redqueen $(ARGS)

calibrate:
	.venv/bin/python -m agni.twin.calibrate

api:
	.venv/bin/uvicorn agni.server.main:app --reload --port 8000

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check agni tests

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__ runs/*.json
