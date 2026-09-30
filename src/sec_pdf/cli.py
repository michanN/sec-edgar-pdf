"""Save Apple's latest 10-K as a PDF from the command line."""

import argparse
import logging
import os
from pathlib import Path

import httpx
from playwright.sync_api import Error as PlaywrightError

from .filings import COMPANIES, latest_filing
from .http import SecClient
from .playwright_renderer import convert_html
from .render import render_pdf

LOG = logging.getLogger(__name__)


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save Apple's latest SEC 10-K as a PDF.")
    parser.add_argument(
        "--contact",
        default=os.getenv("SEC_CONTACT"),
        help="Your name and email address (defaults to SEC_CONTACT)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("output"), help="PDF directory (default: output)"
    )
    args = parser.parse_args(argv)
    if not args.contact or not args.contact.strip():
        parser.error("Set --contact or SEC_CONTACT to your name and email address")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    company = "Apple"
    client = SecClient(args.contact.strip())
    try:
        LOG.info("Submissions URL: https://data.sec.gov/submissions/CIK%s.json", COMPANIES[company])
        filing = latest_filing(client, company)
        LOG.info("Latest %s 10-K filing date: %s", filing.company, filing.filed)
        LOG.info("Report URL: %s", filing.url)
        output = args.output_dir / f"{company.lower()}-{filing.accession}-playwright.pdf"
        render_pdf(client, filing.url, output, converter=convert_html)
        LOG.info("Saved PDF: %s", output.resolve())
        return 0
    except httpx.HTTPStatusError as exc:
        LOG.error("SEC returned HTTP %s for %s", exc.response.status_code, exc.request.url)
        if exc.response.status_code == 429:
            LOG.error("SEC rate limit reached. Stopping requests; try again later.")
        if "retry-after" in exc.response.headers:
            LOG.error("SEC Retry-After: %s", exc.response.headers["retry-after"])
        return 1
    except httpx.RequestError as exc:
        LOG.error("SEC request failed (%s): %s", type(exc).__name__, exc)
        return 1
    except ValueError as exc:
        LOG.error("Could not save Apple's latest 10-K: %s", exc)
        return 1
    except PlaywrightError as exc:
        LOG.error("PDF rendering failed: %s", exc)
        return 1
    except OSError as exc:
        LOG.error("Could not write PDF output: %s", exc)
        return 1
    except (KeyError, TypeError, IndexError) as exc:
        LOG.error("Unexpected SEC submissions data (%s): %s", type(exc).__name__, exc)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
