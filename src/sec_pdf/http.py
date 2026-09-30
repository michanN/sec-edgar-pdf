"""Make requests to the SEC API."""

import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx
import stamina
from pyrate_limiter import Duration, Limiter, Rate

DEFAULT_TIMEOUT_SECONDS = 30
CONNECT_TIMEOUT_SECONDS = 10
REQUESTS_PER_SECOND = 5
MAX_RETRY_AFTER_SECONDS = 60

LOG = logging.getLogger(__name__)


def retry_after_seconds(value: str) -> float:
    """Convert a Retry-After delay or HTTP date to seconds."""
    value = value.strip()
    if value.isdecimal():
        return float(value)
    retry_at = parsedate_to_datetime(value)
    return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())


def should_retry(error: Exception) -> bool | float:
    """Retry temporary failures, respecting server delays up to our waiting limit."""
    if not isinstance(error, httpx.HTTPStatusError):
        return isinstance(error, httpx.TransportError)

    response = error.response
    if response.status_code != 429 and not response.is_server_error:
        return False

    retry_after = response.headers.get("retry-after")
    if retry_after is None:
        return True

    try:
        delay = retry_after_seconds(retry_after)
    except (ValueError, TypeError, OverflowError):
        LOG.error("Stopping: cannot read SEC Retry-After value %r", retry_after)
        return False

    if delay > MAX_RETRY_AFTER_SECONDS:
        LOG.error(
            "Stopping: SEC requested a %.1f-second wait, above our %d-second limit",
            delay,
            MAX_RETRY_AFTER_SECONDS,
        )
        return False
    return delay


class SecClient:
    def __init__(self, contact: str) -> None:
        self.limiter = Limiter(Rate(REQUESTS_PER_SECOND, Duration.SECOND))
        self.client = httpx.Client(
            headers={"User-Agent": f"quartr-sec-pdf/0.1 ({contact})"},
            timeout=httpx.Timeout(
                DEFAULT_TIMEOUT_SECONDS,
                connect=CONNECT_TIMEOUT_SECONDS,
            ),
        )

    @stamina.retry(on=should_retry, attempts=3, timeout=None)
    def get(self, url: str) -> httpx.Response:
        """Fetch a resource with rate limiting and bounded retries."""
        self.limiter.try_acquire("sec")
        response = self.client.get(url)
        response.raise_for_status()
        return response

    def close(self) -> None:
        self.client.close()
        self.limiter.close()
