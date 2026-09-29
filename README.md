# Quartr assignment

The goal is to fetch the latest SEC 10-K reports for the six companies in the [assignment](docs/TASK.md) and save them as PDFs.

## Find Apple's latest 10-K

The current CLI logs the filing date, submissions URL, and primary report URL.
It searches recent submissions only and does not download or render the report yet.

After installing the dependencies with `uv sync --locked`, run:

```sh
export SEC_CONTACT="Your Name your.email@example.com"
uv run sec-pdf
```

You can also pass contact details directly:

```sh
uv run sec-pdf --contact "Your Name your.email@example.com"
```

`--contact` takes precedence over `SEC_CONTACT`. Use your own name and email for the
SEC User-Agent. Run `uv run sec-pdf --help` for usage.

Logs include timestamps. Request or filing-selection failures return exit code `1`.
Missing contact details or invalid arguments return exit code `2`.

## Development

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
uv sync --locked
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
```

Run the offline unit tests with `uv run pytest`.
