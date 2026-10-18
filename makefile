.PHONY: linting tests all

# ── Linting ────────────────────────────────────────────────────────────────────
linting:
	uv run ruff format .
	uv run ruff check --fix --show-fixes --exit-non-zero-on-fix
	uv run mypy

# ── Tests ──────────────────────────────────────────────────────────────────────
tests:
	uv run pytest

# ── Composite ──────────────────────────────────────────────────────────────────
all: linting tests
