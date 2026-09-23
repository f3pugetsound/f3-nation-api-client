import httpx
import pytest

from f3_nation_api import F3NationClient, F3NationClientConfig


@pytest.mark.asyncio
async def test_list_region_aos_fetches_every_active_page() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page_index = int(request.url.params["pageIndex"])
        orgs = [
            {
                "id": page_index + 10,
                "parentId": 38237,
                "name": f"AO {page_index}",
                "orgType": "ao",
                "isActive": True,
                "meta": {"slack_channel_id": f"C{page_index}"},
            }
        ]
        return httpx.Response(200, json={"orgs": orgs, "total": 2})

    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"),
        transport=httpx.MockTransport(handler),
    ) as client:
        aos = await client.list_region_aos(region_id=38237, page_size=1)

    assert [(ao.id, ao.name, ao.slack_channel_id) for ao in aos] == [
        (10, "AO 0", "C0"),
        (11, "AO 1", "C1"),
    ]
    assert len(requests) == 2
    assert requests[0].url.path == "/v1/org"
    assert requests[0].url.params["orgTypes[0]"] == "ao"
    assert requests[0].url.params["parentOrgIds[0]"] == "38237"
    assert requests[0].url.params["statuses[0]"] == "active"
    assert requests[1].url.params["pageIndex"] == "1"


@pytest.mark.asyncio
async def test_list_region_aos_accepts_missing_channel_metadata() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={
                "orgs": [
                    {
                        "id": 10,
                        "parentId": 38237,
                        "name": "AO",
                        "orgType": "ao",
                        "isActive": True,
                        "meta": {},
                    }
                ],
                "total": 1,
            },
        )
    )

    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"), transport=transport
    ) as client:
        aos = await client.list_region_aos(region_id=38237)

    assert aos[0].slack_channel_id is None
