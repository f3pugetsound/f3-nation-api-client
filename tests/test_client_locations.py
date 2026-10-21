import httpx
import pytest

from f3_nation_api import F3NationClient, F3NationClientConfig
from f3_nation_api.errors import F3NationResponseError


@pytest.mark.asyncio
async def test_list_region_locations_fetches_every_active_page() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page_index = int(request.url.params["pageIndex"])
        locations = [
            {
                "id": page_index + 90,
                "locationName": f"OTB-Location {page_index}",
                "regionId": 38237,
                "isActive": True,
            }
        ]
        return httpx.Response(200, json={"locations": locations, "totalCount": 2})

    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"),
        transport=httpx.MockTransport(handler),
    ) as client:
        locations = await client.list_region_locations(region_id=38237, page_size=1)

    assert [(item.id, item.name) for item in locations] == [
        (90, "OTB-Location 0"),
        (91, "OTB-Location 1"),
    ]
    assert len(requests) == 2
    assert requests[0].url.path == "/v1/location"
    assert requests[0].url.params["regionIds[0]"] == "38237"
    assert requests[0].url.params["statuses[0]"] == "active"
    assert requests[1].url.params["pageIndex"] == "1"


@pytest.mark.parametrize(
    ("region_id", "page_size", "message"),
    [(0, 100, "region_id must be positive"), (38237, 0, "page_size must be positive")],
)
@pytest.mark.asyncio
async def test_list_region_locations_rejects_invalid_arguments(
    region_id: int, page_size: int, message: str
) -> None:
    transport = httpx.MockTransport(
        lambda _: pytest.fail("invalid arguments must not make a request")
    )
    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"), transport=transport
    ) as client:
        with pytest.raises(ValueError, match=message):
            await client.list_region_locations(
                region_id=region_id, page_size=page_size
            )


@pytest.mark.parametrize(
    "payload",
    [
        {"locations": {}, "totalCount": 0},
        {"locations": [], "totalCount": True},
        {"locations": [], "totalCount": -1},
    ],
)
@pytest.mark.asyncio
async def test_list_region_locations_rejects_malformed_pagination(
    payload: dict[str, object],
) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"), transport=transport
    ) as client:
        with pytest.raises(F3NationResponseError):
            await client.list_region_locations(region_id=38237)


@pytest.mark.asyncio
async def test_list_region_locations_rejects_premature_end() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"locations": [], "totalCount": 1})
    )
    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"), transport=transport
    ) as client:
        with pytest.raises(
            F3NationResponseError,
            match="location pagination ended before totalCount",
        ):
            await client.list_region_locations(region_id=38237)
