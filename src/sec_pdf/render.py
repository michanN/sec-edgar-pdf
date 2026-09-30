"""Convert reports and validate PDFs before saving them."""

import logging
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from .http import SecClient

LOG = logging.getLogger(__name__)

type Converter = Callable[[SecClient, str, Path], None]


def validate_pdf(path: Path) -> None:
    """Raise ValueError if the PDF cannot be read, has no pages, or has no text."""
    try:
        with path.open("rb") as source:
            reader = PdfReader(source)
            if not reader.pages:
                raise ValueError("PDF has no pages")
            if not any(page.extract_text().strip() for page in reader.pages):
                raise ValueError("PDF has no extractable text")
    except PyPdfError as exc:
        raise ValueError(f"Cannot read PDF: {exc}") from exc


def render_pdf(client: SecClient, url: str, target: Path, converter: Converter) -> None:
    """Convert and validate a temporary PDF before replacing the final file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".sec-pdf-", dir=target.parent) as temporary:
        pending = Path(temporary) / target.name
        converter(client, url, pending)
        LOG.info("Validating PDF")
        validate_pdf(pending)
        pending.replace(target)
