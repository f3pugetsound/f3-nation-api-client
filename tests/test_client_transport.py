import httpx
import pytest

from f3_nation_api.client import F3NationClient, F3NationClientConfig
from f3_nation_api.errors import (
    F3NationAuthenticationError,
    F3NationRateLimitError,
    F3NationResponseError,
    F3NationServerError,
)


@pytest.mark.asyncio
async def test_request_sends_required_headers_and_base_url() -> None:
    captured: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request
        return httpx.Response(200, json={"ok": True})

    async with F3NationClient(
        F3NationClientConfig(api_key="super-secret", client_name="tagorama"),
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await client.get_json("/v1/ping")

    assert result == {"ok": True}
    assert captured is not None
    assert str(captured.url) == "https://api.f3nation.com/v1/ping"
    assert captured.headers["Authorization"] == "Bearer super-secret"
    assert captured.headers["Client"] == "tagorama"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_authentication_errors_do_not_expose_secret(status: int) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(status, json={"error": "Bearer super-secret"})
    )

    with pytest.raises(F3NationAuthenticationError) as captured:
        async with F3NationClient(
            F3NationClientConfig(api_key="super-secret", client_name="tagorama"),
            transport=transport,
        ) as client:
            await client.get_json("/v1/ping")

    assert "super-secret" not in str(captured.value)


@pytest.mark.asyncio
async def test_rate_limit_is_retried_then_succeeds() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True})

    async with F3NationClient(
        F3NationClientConfig(
            api_key="key", client_name="tagorama", max_retries=2, retry_base_delay=0
        ),
        transport=httpx.MockTransport(handler),
    ) as client:
        assert await client.get_json("/v1/ping") == {"ok": True}

    assert attempts == 3


@pytest.mark.asyncio
async def test_exhausted_rate_limit_has_typed_error() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(429))

    with pytest.raises(F3NationRateLimitError):
        async with F3NationClient(
            F3NationClientConfig(
                api_key="key", client_name="tagorama", max_retries=1, retry_base_delay=0
            ),
            transport=transport,
        ) as client:
            await client.get_json("/v1/ping")


@pytest.mark.asyncio
async def test_server_errors_are_retried_then_raise() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    with pytest.raises(F3NationServerError):
        async with F3NationClient(
            F3NationClientConfig(
                api_key="key", client_name="tagorama", max_retries=2, retry_base_delay=0
            ),
            transport=httpx.MockTransport(handler),
        ) as client:
            await client.get_json("/v1/ping")

    assert attempts == 3


@pytest.mark.asyncio
async def test_timeout_is_retried_then_raise() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(F3NationServerError, match="network request failed"):
        async with F3NationClient(
            F3NationClientConfig(
                api_key="key", client_name="tagorama", max_retries=1, retry_base_delay=0
            ),
            transport=httpx.MockTransport(handler),
        ) as client:
            await client.get_json("/v1/ping")

    assert attempts == 2


@pytest.mark.asyncio
async def test_non_object_json_is_rejected() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=[]))

    with pytest.raises(F3NationResponseError, match="JSON object"):
        async with F3NationClient(
            F3NationClientConfig(api_key="key", client_name="tagorama"),
            transport=transport,
        ) as client:
            await client.get_json("/v1/ping")
