from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import Mock, call, patch

import httpx
import pytest
import stamina

from sec_pdf.http import SecClient, should_retry

URL = "https://data.sec.gov/submissions/CIK0000320193.json"
REQUEST = httpx.Request("GET", URL)


@pytest.fixture
def mock_client() -> Iterator[tuple[SecClient, Mock, Mock]]:
    client = SecClient("Test User test@example.com")
    try:
        with (
            patch.object(client.client, "get") as get,
            patch.object(client.limiter, "try_acquire", return_value=True) as acquire,
            # Remove backoff without replacing the client's three-attempt limit.
            stamina.set_testing(True, attempts=10, cap=True),
        ):
            yield client, get, acquire
    finally:
        client.close()


@pytest.mark.parametrize(
    "first_failure",
    [
        httpx.Response(503, request=REQUEST),
        httpx.ReadTimeout("Read timed out", request=REQUEST),
        httpx.Response(429, request=REQUEST),
        httpx.Response(429, headers={"Retry-After": "60"}, request=REQUEST),
    ],
    ids=["server-error", "timeout", "rate-limit", "rate-limit-with-delay"],
)
def test_recovers_from_transient_failure(
    mock_client: tuple[SecClient, Mock, Mock],
    first_failure: httpx.Response | httpx.TransportError,
) -> None:
    client, get, acquire = mock_client
    success = httpx.Response(200, json={"name": "Apple Inc."}, request=REQUEST)
    get.side_effect = [first_failure, success]

    response = client.get(URL)

    assert response is success
    assert get.call_args_list == [call(URL), call(URL)]
    assert acquire.call_args_list == [call("sec"), call("sec")]


@pytest.mark.parametrize("status_code", [503, 429])
def test_stops_after_three_failed_attempts(
    mock_client: tuple[SecClient, Mock, Mock], status_code: int
) -> None:
    client, get, acquire = mock_client
    failure = httpx.Response(status_code, request=REQUEST)
    get.return_value = failure

    with pytest.raises(httpx.HTTPStatusError) as error:
        client.get(URL)

    assert error.value.response is failure
    assert get.call_count == 3
    assert acquire.call_count == 3


@pytest.mark.parametrize("status_code", [403, 404])
def test_does_not_retry_permanent_http_errors(
    mock_client: tuple[SecClient, Mock, Mock], status_code: int
) -> None:
    client, get, acquire = mock_client
    failure = httpx.Response(status_code, request=REQUEST)
    get.return_value = failure

    with pytest.raises(httpx.HTTPStatusError) as error:
        client.get(URL)

    assert error.value.response is failure
    get.assert_called_once_with(URL)
    acquire.assert_called_once_with("sec")


@pytest.mark.parametrize("status_code", [429, 503])
@pytest.mark.parametrize(
    ("retry_after", "expected_delay"),
    [
        ("0", 0.0),
        ("60", 60.0),
        ("Wed, 30 Sep 2026 12:00:30 GMT", 30.0),
        ("Wed, 30 Sep 2026 11:59:30 GMT", 0.0),
    ],
    ids=["zero-delay", "maximum-delay", "future-date", "past-date"],
)
def test_retry_after_supplies_server_delay(
    status_code: int, retry_after: str, expected_delay: float
) -> None:
    response = httpx.Response(status_code, headers={"Retry-After": retry_after}, request=REQUEST)
    error = httpx.HTTPStatusError("Temporary SEC failure", request=REQUEST, response=response)

    with patch("sec_pdf.http.datetime") as clock:
        clock.now.return_value = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
        delay = should_retry(error)

    # Stamina treats False as "stop", but 0.0 as "retry immediately".
    assert isinstance(delay, float)
    assert delay == expected_delay


@pytest.mark.parametrize(
    ("retry_after", "message"),
    [
        ("61", "above our 60-second limit"),
        ("invalid", "cannot read SEC Retry-After"),
    ],
    ids=["too-long", "unreadable"],
)
def test_stops_when_retry_after_cannot_be_honored(
    mock_client: tuple[SecClient, Mock, Mock],
    caplog: pytest.LogCaptureFixture,
    retry_after: str,
    message: str,
) -> None:
    client, get, acquire = mock_client
    failure = httpx.Response(429, headers={"Retry-After": retry_after}, request=REQUEST)
    get.return_value = failure

    with pytest.raises(httpx.HTTPStatusError) as error:
        client.get(URL)

    assert error.value.response is failure
    assert message in caplog.text
    get.assert_called_once_with(URL)
    acquire.assert_called_once_with("sec")
