import base64
import gzip
from pathlib import Path
from unittest.mock import Mock, call, patch

import httpx
import pytest
from pypdf import PdfReader, PdfWriter

from sec_pdf.cli import main
from sec_pdf.http import SecClient
from sec_pdf.render import validate_pdf

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0000320193.json"
REPORT_DIR = "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/"
REPORT_URL = REPORT_DIR + "aapl-20250927.htm"
FILENAME = "apple-0000320193-25-000079-playwright.pdf"


@pytest.fixture
def resources() -> dict[str, httpx.Response]:
    html = b"""<!doctype html>
        <html><head><link rel="stylesheet" href="report.css"></head>
        <body><h1>Apple annual report</h1><p>Revenue for the fiscal year.</p>
        <img src="logo.png" alt="Company logo"></body></html>"""
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1s"
        "AAAAASUVORK5CYII="
    )
    return {
        SUBMISSIONS_URL: httpx.Response(
            200,
            json={
                "filings": {
                    "recent": {
                        "form": ["10-K"],
                        "filingDate": ["2025-10-31"],
                        "acceptanceDateTime": ["2025-10-31T10:00:00.000Z"],
                        "accessionNumber": ["0000320193-25-000079"],
                        "primaryDocument": ["aapl-20250927.htm"],
                    }
                }
            },
        ),
        REPORT_URL: httpx.Response(
            200,
            headers={"Content-Type": "text/html", "Content-Encoding": "gzip"},
            content=gzip.compress(html),
        ),
        REPORT_DIR + "report.css": httpx.Response(
            200,
            headers={"Content-Type": "text/css"},
            text="h1 { color: navy; } img { width: 30px; height: 30px; }",
        ),
        REPORT_DIR + "logo.png": httpx.Response(
            200, headers={"Content-Type": "image/png"}, content=png
        ),
    }


@pytest.fixture
def mock_get(resources: dict[str, httpx.Response], monkeypatch: pytest.MonkeyPatch) -> Mock:
    def fetch(url: str) -> httpx.Response:
        response = resources[url]
        response.request = httpx.Request("GET", url)
        response.raise_for_status()
        return response

    get = Mock(side_effect=fetch)
    monkeypatch.setattr(SecClient, "get", get)
    return get


def test_saves_pdf_using_sec_client_for_html_and_assets(
    tmp_path: Path, mock_get: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO"):
        result = main(
            [
                "--contact",
                "Test User test@example.com",
                "--output-dir",
                str(tmp_path),
                "--companies",
                "apple",
            ]
        )

    output = tmp_path / FILENAME
    assert result == 0
    assert list(tmp_path.iterdir()) == [output]
    assert "Apple annual report" in PdfReader(output).pages[0].extract_text()
    assert str(output) in caplog.text
    assert mock_get.call_count == 4
    mock_get.assert_has_calls(
        [
            call(SUBMISSIONS_URL),
            call(REPORT_URL),
            call(REPORT_DIR + "report.css"),
            call(REPORT_DIR + "logo.png"),
        ],
        any_order=True,
    )


def test_failed_asset_download_preserves_existing_pdf(
    tmp_path: Path, resources: dict[str, httpx.Response], mock_get: Mock
) -> None:
    resources[REPORT_DIR + "logo.png"] = httpx.Response(503)
    output = tmp_path / FILENAME
    output.write_bytes(b"previous PDF")

    result = main(
        [
            "--contact",
            "Test User test@example.com",
            "--output-dir",
            str(tmp_path),
            "--companies",
            "apple",
        ]
    )

    assert result == 1
    assert output.read_bytes() == b"previous PDF"
    assert list(tmp_path.iterdir()) == [output]


def test_saves_pdfs_before_and_after_a_company_failure(
    tmp_path: Path,
    resources: dict[str, httpx.Response],
    mock_get: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    meta_url = "https://data.sec.gov/submissions/CIK0001326801.json"
    resources[meta_url] = httpx.Response(200, json={"filings": {"recent": {"form": ["10-Q"]}}})

    # Reuse Apple's report and assets for a second successful company.
    netflix_url = "https://data.sec.gov/submissions/CIK0001065280.json"
    netflix_dir = "https://www.sec.gov/Archives/edgar/data/1065280/000106528026000034/"
    submissions = resources[SUBMISSIONS_URL].json()
    submissions["filings"]["recent"]["accessionNumber"] = ["0001065280-26-000034"]
    submissions["filings"]["recent"]["primaryDocument"] = ["nflx-20251231.htm"]
    resources[netflix_url] = httpx.Response(200, json=submissions)
    resources[netflix_dir + "nflx-20251231.htm"] = httpx.Response(
        200,
        headers={"Content-Type": "text/html"},
        content=resources[REPORT_URL].content.replace(
            b"Apple annual report", b"Netflix annual report"
        ),
    )
    for asset in ("report.css", "logo.png"):
        resources[netflix_dir + asset] = resources[REPORT_DIR + asset]

    with (
        caplog.at_level("INFO", logger="sec_pdf"),
        patch.object(SecClient, "close", autospec=True, side_effect=SecClient.close) as close,
    ):
        result = main(
            [
                "--contact",
                "Test User test@example.com",
                "--output-dir",
                str(tmp_path),
                "--companies",
                "apple",
                "meta",
                "netflix",
            ]
        )

    apple_pdf = tmp_path / FILENAME
    netflix_pdf = tmp_path / "netflix-0001065280-26-000034-playwright.pdf"
    assert result == 1
    assert set(tmp_path.iterdir()) == {apple_pdf, netflix_pdf}
    for output, company in [(apple_pdf, "Apple"), (netflix_pdf, "Netflix")]:
        assert f"{company} annual report" in PdfReader(output).pages[0].extract_text()
    submission_calls = [
        request for request in mock_get.call_args_list if "/submissions/" in request.args[0]
    ]
    assert submission_calls == [call(SUBMISSIONS_URL), call(meta_url), call(netflix_url)]
    assert "No 10-K in recent filings for Meta" in caplog.text
    assert "Saved 2/3 PDFs" in caplog.text
    assert "1 failed, 0 not attempted" in caplog.text
    close.assert_called_once()


def test_rejects_unreadable_pdf(tmp_path: Path) -> None:
    output = tmp_path / "broken.pdf"
    output.write_bytes(b"not a PDF")

    with pytest.raises(ValueError, match="Cannot read PDF"):
        validate_pdf(output)


@pytest.mark.parametrize(
    ("pages", "message"), [(0, "PDF has no pages"), (1, "PDF has no extractable text")]
)
def test_rejects_pdf_without_pages_or_text(tmp_path: Path, pages: int, message: str) -> None:
    output = tmp_path / "empty.pdf"
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    writer.write(output)

    with pytest.raises(ValueError, match=message):
        validate_pdf(output)
