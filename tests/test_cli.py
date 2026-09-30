from pathlib import Path
from unittest.mock import Mock, call

import httpx
import pytest

from sec_pdf.cli import main
from sec_pdf.http import SecClient

CONTACT = "Test User test@example.com"


@pytest.fixture
def mock_batch(monkeypatch: pytest.MonkeyPatch) -> tuple[Mock, Mock]:
    client_factory = Mock(return_value=Mock(spec=SecClient))
    process = Mock()
    monkeypatch.setattr("sec_pdf.cli.SecClient", client_factory)
    monkeypatch.setattr("sec_pdf.cli.process_company", process)
    return client_factory, process


@pytest.mark.parametrize(
    ("selection", "expected_companies"),
    [
        ([], ["Apple", "Meta", "Alphabet", "Amazon", "Netflix", "Goldman Sachs"]),
        (
            ["--companies", "NETFLIX", "apple", "Netflix", "Goldman Sachs"],
            ["Netflix", "Apple", "Goldman Sachs"],
        ),
    ],
    ids=["all-by-default", "selected-in-order-without-duplicates"],
)
def test_processes_companies_with_one_shared_client(
    tmp_path: Path,
    mock_batch: tuple[Mock, Mock],
    selection: list[str],
    expected_companies: list[str],
) -> None:
    client_factory, process = mock_batch
    client = client_factory.return_value

    result = main(["--contact", CONTACT, "--output-dir", str(tmp_path), *selection])

    assert result == 0
    client_factory.assert_called_once_with(CONTACT)
    assert process.call_args_list == [
        call(client, company, tmp_path) for company in expected_companies
    ]
    client.close.assert_called_once_with()


@pytest.mark.parametrize(
    ("status_code", "headers"),
    [(403, {}), (429, {}), (503, {"Retry-After": "120"})],
    ids=["forbidden", "rate-limit", "server-delay"],
)
def test_stops_batch_after_sec_access_failure(
    tmp_path: Path,
    mock_batch: tuple[Mock, Mock],
    caplog: pytest.LogCaptureFixture,
    status_code: int,
    headers: dict[str, str],
) -> None:
    client_factory, process = mock_batch
    client = client_factory.return_value
    request = httpx.Request("GET", "https://data.sec.gov/submissions/CIK0001326801.json")
    response = httpx.Response(status_code, headers=headers, request=request)
    failure = httpx.HTTPStatusError("SEC access failed", request=request, response=response)
    process.side_effect = [None, failure, None]

    with caplog.at_level("INFO", logger="sec_pdf"):
        result = main(
            [
                "--contact",
                CONTACT,
                "--output-dir",
                str(tmp_path),
                "--companies",
                "apple",
                "meta",
                "netflix",
            ]
        )

    assert result == 1
    assert process.call_args_list == [
        call(client, "Apple", tmp_path),
        call(client, "Meta", tmp_path),
    ]
    assert "Saved 1/3 PDFs" in caplog.text
    assert "1 failed, 1 not attempted" in caplog.text
    client.close.assert_called_once_with()
