import pytest

from sec_pdf.filings import select_filing


def test_selects_newest_exact_10_k_using_acceptance_time_for_ties() -> None:
    # Earlier acceptance, newer amendment, expected filing, older annual report.
    data = {
        "filings": {
            "recent": {
                "form": ["10-K", "10-K/A", "10-K", "10-K"],
                "filingDate": ["2025-10-31", "2025-11-03", "2025-10-31", "2024-11-01"],
                "acceptanceDateTime": [
                    "2025-10-31T10:00:00.000Z",
                    "2025-11-03T12:00:00.000Z",
                    "2025-10-31T11:00:00.000Z",
                    "2024-11-01T12:00:00.000Z",
                ],
                "accessionNumber": [
                    "0000320193-25-000078",
                    "0000320193-25-000080",
                    "0000320193-25-000079",
                    "0000320193-24-000123",
                ],
                "primaryDocument": [
                    "earlier.htm",
                    "amendment.htm",
                    "aapl-20250927.htm",
                    "aapl-20240928.htm",
                ],
            }
        }
    }

    filing = select_filing("Apple", data)

    assert filing.company == "Apple"
    assert filing.filed == "2025-10-31"
    assert filing.accession == "0000320193-25-000079"
    assert filing.url == (
        "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm"
    )


def test_raises_clear_error_when_no_exact_10_k_exists() -> None:
    data = {"filings": {"recent": {"form": ["10-Q", "10-K/A", "8-K"]}}}

    with pytest.raises(ValueError, match="^No 10-K in recent filings for Apple$"):
        select_filing("Apple", data)
