"""Save the latest 10-K reports as PDFs from the command line."""

import argparse
import logging
import os
from pathlib import Path
from typing import Literal

import httpx

from .filings import COMPANIES, latest_filing
from .http import SecClient
from .playwright_renderer import convert_html
from .render import render_pdf

LOG = logging.getLogger(__name__)


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save the latest SEC 10-K reports as PDFs.")
    parser.add_argument(
        "--contact",
        default=os.getenv("SEC_CONTACT"),
        help="Your name and email address (defaults to SEC_CONTACT)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("output"), help="PDF directory (default: output)"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show filing details and individual HTTP requests"
    )
    parser.add_argument("--refresh", action="store_true", help="Regenerate existing PDFs")
    company_names = {name.casefold(): name for name in COMPANIES}
    parser.add_argument(
        "--companies",
        nargs="+",
        type=str.casefold,
        choices=list(company_names),
        help="Companies to fetch (default: all six)",
    )
    args = parser.parse_args(argv)
    args.companies = (
        [company_names[name] for name in dict.fromkeys(args.companies)]
        if args.companies is not None
        else list(COMPANIES)
    )
    if not args.contact or not args.contact.strip():
        parser.error("Set --contact or SEC_CONTACT to your name and email address")
    return args


def process_company(
    client: SecClient, company: str, output_dir: Path, *, refresh: bool = False
) -> Literal["saved", "reused"]:
    """Find the latest 10-K and reuse its PDF unless refresh is requested."""
    LOG.debug("Submissions URL: https://data.sec.gov/submissions/CIK%s.json", COMPANIES[company])
    filing = latest_filing(client, company)
    LOG.debug("Latest %s 10-K filing date: %s", company, filing.filed)
    LOG.info("Report URL: %s", filing.url)
    slug = company.lower().replace(" ", "-")
    output = output_dir / f"{slug}-{filing.accession}-playwright.pdf"
    if output.is_file():
        if not refresh:
            LOG.info("%s: reusing existing PDF: %s", company, output.resolve())
            return "reused"
        LOG.info("%s: refreshing existing PDF", company)
    render_pdf(client, filing.url, output, converter=convert_html)
    LOG.info("%s: saved PDF: %s", company, output.resolve())
    return "saved"


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("sec_pdf").setLevel(logging.DEBUG if args.verbose else logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO if args.verbose else logging.WARNING)

    client = SecClient(args.contact.strip())
    total = len(args.companies)
    saved = reused = failed = 0
    try:
        for index, company in enumerate(args.companies, start=1):
            LOG.info("[%d/%d] %s: finding latest 10-K", index, total, company)
            try:
                outcome = process_company(client, company, args.output_dir, refresh=args.refresh)
                if outcome == "reused":
                    reused += 1
                else:
                    saved += 1
            except Exception as exc:
                failed += 1
                LOG.error("%s: %s", company, str(exc) or type(exc).__name__)
                LOG.debug("Failure details", exc_info=True)
                if isinstance(exc, httpx.HTTPStatusError):
                    response = exc.response
                    if "retry-after" in response.headers:
                        LOG.error("SEC Retry-After: %s", response.headers["retry-after"])
                    if response.status_code in (403, 429) or "retry-after" in response.headers:
                        LOG.error(
                            "Stopping batch after SEC HTTP %d; %d companies not attempted",
                            response.status_code,
                            total - index,
                        )
                        break
    finally:
        client.close()

    LOG.info(
        "Finished: %d saved, %d reused, %d failed, %d not attempted.",
        saved,
        reused,
        failed,
        total - saved - reused - failed,
    )
    return 0 if saved + reused == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
