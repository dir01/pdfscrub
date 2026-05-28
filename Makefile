.PHONY: install test find scrub clean

install:
	uv sync

test:
	uv run pytest -v

# Usage: make find PDF=file.pdf TERMS="John Doe"
find:
	uv run pdfscrub find $(PDF) $(TERMS)

# Usage: make scrub PDF=file.pdf TERMS="John Doe"
scrub:
	uv run pdfscrub scrub $(PDF) $(TERMS)

clean:
	rm -rf .venv __pycache__ src/pdfscrub/__pycache__ tests/__pycache__ .pytest_cache
