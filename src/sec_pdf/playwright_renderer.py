"""Render reports with Chromium, fetching their resources through the SEC client."""

import logging
from pathlib import Path

import httpx
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Route, sync_playwright

from .http import SecClient

LOG = logging.getLogger(__name__)
PAGE_TIMEOUT_MS = 300_000


def convert_html(client: SecClient, url: str, output: Path) -> None:
    """Write a PDF, or raise if downloading or rendering fails."""
    download_error: httpx.HTTPError | None = None

    def fetch_resource(route: Route) -> None:
        nonlocal download_error
        if download_error is not None:
            route.abort()
            return
        try:
            response = client.get(route.request.url)
        except httpx.HTTPError as exc:
            download_error = exc
            route.abort()
            return

        # HTTPX has already decompressed the body. Do not forward its encoding
        # or content-length headers alongside these decoded bytes.
        route.fulfill(
            status=response.status_code,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            body=response.content,
        )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(
                offline=True, service_workers="block", java_script_enabled=False
            )
            context.route("**/*", fetch_resource)
            page = context.new_page()
            page.set_default_timeout(PAGE_TIMEOUT_MS)
            page.emulate_media(media="print")
            LOG.info("Fetching report HTML and assets")
            try:
                page.goto(url, wait_until="load")
                page.wait_for_function("document.fonts.status === 'loaded'")
            except PlaywrightError:
                if download_error is not None:
                    raise download_error from None
                raise
            if download_error is not None:
                raise download_error

            LOG.info("Rendering PDF with Playwright")
            page.pdf(
                path=str(output),
                format="Letter",
                print_background=True,
                prefer_css_page_size=True,
            )
        finally:
            browser.close()
