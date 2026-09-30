# Sec Edgar to PDF Converter

A Python CLI that downloads the latest SEC 10-K reports for Apple, Meta, Alphabet,
Amazon, Netflix, and Goldman Sachs and saves them as PDFs.

## Run with Docker

From the repository directory, build the image and run all six companies.
Use your own name and email for SEC requests.

```sh
docker build -t quartr-sec-pdf .
export SEC_CONTACT="Your Name your.email@example.com"
docker run --rm --init --user "$(id -u):$(id -g)" \
  -e SEC_CONTACT \
  --mount "type=bind,source=$PWD,target=/workspace" \
  quartr-sec-pdf --output-dir /workspace/output
```

These commands use a Unix shell. Docker includes all dependencies and creates
`output/` automatically.

## Run without Docker

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
uv sync --locked
uv run playwright install chromium
export SEC_CONTACT="Your Name your.email@example.com"
uv run sec-pdf
```

On Linux, if browser libraries are missing, run
`uv run playwright install --with-deps chromium`.

## Choose your run

```sh
uv run sec-pdf                                     # All six companies
uv run sec-pdf --companies apple "Goldman Sachs"    # Selected companies
uv run sec-pdf --companies apple --refresh         # Regenerate Apple's PDF
uv run sec-pdf --verbose                           # More detailed logs
```

For Docker, append the same options to the run command above. Use `--help` to see
all options.

## Output

PDFs are saved in `output/`, for example
`apple-0000320193-25-000079-playwright.pdf`.

Each run checks for the latest filing and reuses its PDF if already saved.
Use `--refresh` to download and render it again.

## Checks and decisions

PDFs are checked for readable content before saving. Offline tests cover report
selection, retries, rendering, reuse, and failures. Run them with `uv run pytest`,
or inside Docker:

```sh
docker run --rm --init --network none --entrypoint pytest quartr-sec-pdf -q
```

See [NOTES.md](docs/NOTES.md) for the choices behind the CLI, sequential processing,
Playwright, and the current limitations.
