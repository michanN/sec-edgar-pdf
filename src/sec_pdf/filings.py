"""Find the latest 10-K filing for a supported company."""

from dataclasses import dataclass
from typing import Any

from .http import SecClient

COMPANIES: dict[str, str] = {
    "Apple": "0000320193",
    "Meta": "0001326801",
    "Alphabet": "0001652044",
    "Amazon": "0001018724",
    "Netflix": "0001065280",
    "Goldman Sachs": "0000886982",
}


@dataclass(frozen=True)
class Filing:
    company: str
    accession: str
    filed: str
    url: str


def select_filing(company: str, data: dict[str, Any]) -> Filing:
    """Select the latest exact 10-K by filing date, then acceptance time."""
    recent = data["filings"]["recent"]
    candidates = [index for index, form in enumerate(recent["form"]) if form == "10-K"]

    if not candidates:
        raise ValueError(f"No 10-K in recent filings for {company}")

    index = max(
        candidates,
        key=lambda index: (
            recent["filingDate"][index],
            recent["acceptanceDateTime"][index],
        ),
    )

    accession = recent["accessionNumber"][index]
    primary_document = recent["primaryDocument"][index]
    cik = int(COMPANIES[company])

    url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik}/"
        f"{accession.replace('-', '')}/{primary_document}"
    )

    return Filing(
        company=company,
        accession=accession,
        filed=recent["filingDate"][index],
        url=url,
    )


def latest_filing(client: SecClient, company: str) -> Filing:
    """Find a company's latest 10-K using its recent SEC submissions."""
    cik = COMPANIES[company]
    response = client.get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    return select_filing(company, response.json())
