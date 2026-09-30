# Quartr assignment

The goal is to fetch the latest SEC 10-K reports for the six companies in the [assignment](docs/TASK.md) and save them as PDFs.

## Save the latest 10-K reports as PDFs

The CLI processes all six companies sequentially by default, finding each company's
latest exact 10-K in recent submissions and rendering it with Playwright's Chromium.
HTML, images, stylesheets, and fonts are fetched through
the same SEC client, including its rate limiter and retry policy.

Install the dependencies and Chromium:

```sh
uv sync --locked
uv run playwright install chromium
```

On Linux, if browser system libraries are missing, use
`uv run playwright install --with-deps chromium` to install them as well.

Then run:

```sh
export SEC_CONTACT="Your Name your.email@example.com"
uv run sec-pdf
```

Select companies by name, or pass contact details directly:

```sh
uv run sec-pdf --companies apple netflix "Goldman Sachs"
uv run sec-pdf --contact "Your Name your.email@example.com"
```

Names are case-insensitive; duplicates are removed while preserving selection order.

PDFs go to `output/` by default. Use `--output-dir reports` to choose another directory.
Filenames include company, accession number, and renderer, for example
`apple-0000320193-25-000079-playwright.pdf`.

Existing PDFs are reused after checking submissions for the latest filing. Use
`--refresh` to download and regenerate them. Logs distinguish reuse from refreshing.

Only the final PDF is retained. Before saving, validation checks that it opens,
has pages, and contains extractable text. These basic checks do not guarantee
visual fidelity or complete report content. Failed runs remove the temporary PDF
and leave any previously saved PDF unchanged.

`--contact` takes precedence over `SEC_CONTACT`. Use your own name and email for the
SEC User-Agent. Run `uv run sec-pdf --help` for usage.

Logs show timestamped progress, the report URL, and the final save path. Add `--verbose`
to show filing details and individual HTTP requests. Warnings and errors appear in both modes.
Request, filing-selection, rendering, validation, or output failures return exit code `1`.
Missing contact details or invalid arguments return exit code `2`.
Company-specific failures let the batch continue. SEC 403/429 responses or a final
HTTP error with `Retry-After` stop the batch. The summary lists saved, reused, failed, and
unattempted counts.

## Development

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
uv sync --locked
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
```

Run the offline tests with `uv run pytest`. Renderer tests use the installed
Chromium with fake SEC responses; they make no live SEC requests.
