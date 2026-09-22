import httpx
import pytest

from f3_nation_api import F3NationClient, F3NationClientConfig
from f3_nation_api.errors import F3NationAmbiguousMatchError, F3NationNotFoundError


def ao_payload(identifier: int, name: str, region_id: int) -> dict[str, object]:
    return {
        "id": identifier,
        "name": name,
        "regionId": region_id,
        "regionName": "Puget Sound",
        "locationId": 9,
        "latitude": 47.6,
        "longitude": -122.3,
        "eventCount": 2,
    }


@pytest.mark.asyncio
async def test_search_aos_uses_search_endpoint() -> None:
    captured: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request
        return httpx.Response(200, json={"aos": [ao_payload(42, "Hiawatha", 7)]})

    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"),
        transport=httpx.MockTransport(handler),
    ) as client:
        aos = await client.search_aos("Hiawatha")

    assert [ao.id for ao in aos] == [42]
    assert captured is not None
    assert captured.url.path == "/v1/org-chart/aos"
    assert captured.url.params["searchTerm"] == "Hiawatha"


@pytest.mark.asyncio
async def test_find_ao_exact_is_case_insensitive_and_region_scoped() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={
                "aos": [
                    ao_payload(42, "Hiawatha", 7),
                    ao_payload(99, "Hiawatha", 8),
                    ao_payload(43, "Hiawatha Ridge", 7),
                ]
            },
        )
    )

    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"), transport=transport
    ) as client:
        ao = await client.find_ao_exact("  hIAWATHA ", region_id=7)

    assert ao.id == 42


@pytest.mark.asyncio
async def test_find_ao_exact_rejects_missing_match() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"aos": []}))

    with pytest.raises(F3NationNotFoundError, match="No AO named"):
        async with F3NationClient(
            F3NationClientConfig(api_key="key", client_name="test"), transport=transport
        ) as client:
            await client.find_ao_exact("Missing", region_id=7)


@pytest.mark.asyncio
async def test_find_ao_exact_rejects_ambiguous_match() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={"aos": [ao_payload(42, "Hiawatha", 7), ao_payload(44, "HIAWATHA", 7)]},
        )
    )

    with pytest.raises(F3NationAmbiguousMatchError, match="Multiple AOs"):
        async with F3NationClient(
            F3NationClientConfig(api_key="key", client_name="test"), transport=transport
        ) as client:
            await client.find_ao_exact("Hiawatha", region_id=7)
