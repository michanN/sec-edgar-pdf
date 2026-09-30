# Repository Guidelines

## Project structure and scope

Python source lives in `src/sec_pdf/`: `cli.py` handles arguments and logging,
`http.py` wraps HTTPX, and `filings.py` holds company mappings and filing selection.
Offline tests live in `tests/`. Follow `docs/TASK.md` for requirements and
`docs/NOTES.md` for scope decisions.

## Build, test, and development commands

Use Python 3.13+ and uv:

- `uv sync --locked`: install dependencies from the lockfile.
- `uv run sec-pdf --help`: display CLI usage.
- `uv run sec-pdf`: fetch Apple's latest filing metadata using `SEC_CONTACT`.
- `uv run pytest`: run offline unit tests.
- `uv run ruff check src tests`: check lint rules.
- `uv run ruff format --check src tests`: verify formatting; omit `--check` to format.
- `uv run mypy`: run strict type checking on application code.
- `uv build`: build distribution packages with Hatchling.

## Coding style and naming

Use four-space indentation, type annotations, and a 100-character line limit.
Use `snake_case` for functions and variables, `PascalCase` for classes, and
`UPPER_CASE` for constants. Let Ruff manage formatting and import ordering.
Prefer straightforward functions and clear errors over speculative abstractions.
Close HTTP clients after use, including failure paths.

## Testing guidelines

Use pytest with `test_*.py` files and descriptive `test_*` functions. Keep fixtures
small and readable. Tests must use fake SEC data and make no live network calls.
No coverage threshold is configured; add tests for meaningful behavior rather than coverage alone.

## Commits and pull requests

Git history is short, with a recent `feat:` commit. Prefer concise, descriptive
messages such as `feat: add PDF rendering` or `fix: correct filing selection`.
Keep pull requests focused; describe the behavior change, relevant limitations,
and checks run. Update README usage when commands change, and record agreed
scope decisions in `docs/NOTES.md`. Preserve the AI prompt log required by the assignment.

## Configuration

Set `SEC_CONTACT="Your Name your.email@example.com"`, or pass `--contact` to override
it. Use your own contact details for the SEC User-Agent. Keep personal contact
details out of committed examples and test fixtures.
