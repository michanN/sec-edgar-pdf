"""Make requests to the SEC API."""

import httpx

DEFAULT_TIMEOUT_SECONDS = 30
CONNECT_TIMEOUT_SECONDS = 10


class SecClient:
    def __init__(self, contact: str) -> None:
        self.client = httpx.Client(
            headers={"User-Agent": f"quartr-sec-pdf/0.1 ({contact})"},
            timeout=httpx.Timeout(
                DEFAULT_TIMEOUT_SECONDS,
                connect=CONNECT_TIMEOUT_SECONDS,
            ),
        )

    def get(self, url: str) -> httpx.Response:
        """Fetch a resource and raise an HTTP error for unsuccessful responses."""
        response = self.client.get(url)
        response.raise_for_status()
        return response

    def close(self) -> None:
        self.client.close()
