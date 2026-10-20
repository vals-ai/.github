.PHONY: format typecheck test
format:
	uv run ruff format .github/security-review tests
	uv run ruff check --fix .github/security-review tests

typecheck:
	uv run basedpyright

test:
	uv run pytest -q
