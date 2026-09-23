from datetime import date

import httpx
import pytest

from f3_nation_api import F3NationClient, F3NationClientConfig


def event_payload(identifier: int, start_date: str) -> dict[str, object]:
    return {
        "id": identifier,
        "name": f"Event {identifier}",
        "isActive": True,
        "orgId": 42,
        "aoName": "The AO",
        "startDate": start_date,
        "paxCount": 8,
        "fngCount": 1,
    }


@pytest.mark.asyncio
async def test_list_event_instances_fetches_every_page_with_date_filters() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page_index = int(request.url.params["pageIndex"])
        if page_index == 0:
            events = [event_payload(1, "2026-09-01"), event_payload(2, "2026-09-08")]
        else:
            events = [event_payload(3, "2026-09-15")]
        return httpx.Response(200, json={"eventInstances": events, "totalCount": 3})

    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"),
        transport=httpx.MockTransport(handler),
    ) as client:
        events = await client.list_event_instances(
            ao_id=42,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
            page_size=2,
        )

    assert [event.id for event in events] == [1, 2, 3]
    assert events[0].ao_name == "The AO"
    assert events[0].pax_count == 8
    assert events[0].fng_count == 1
    assert len(requests) == 2
    assert requests[0].url.path == "/v1/event-instance"
    assert requests[0].url.params["aoOrgId"] == "42"
    assert requests[0].url.params["startDate"] == "2026-09-01"
    assert requests[0].url.params["startDateTo"] == "2026-09-30"
    assert requests[1].url.params["pageIndex"] == "1"


@pytest.mark.asyncio
async def test_list_event_instances_accepts_empty_result() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"eventInstances": [], "totalCount": 0})
    )

    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"), transport=transport
    ) as client:
        events = await client.list_event_instances(
            ao_id=42,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
        )

    assert events == ()


@pytest.mark.asyncio
async def test_list_event_instances_can_select_a_region() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"eventInstances": [], "totalCount": 0})

    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"),
        transport=httpx.MockTransport(handler),
    ) as client:
        await client.list_event_instances(
            region_id=38237,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
        )

    assert requests[0].url.params["regionOrgId"] == "38237"
    assert "aoOrgId" not in requests[0].url.params


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("ao_id", "region_id"),
    [(None, None), (42, 38237)],
)
async def test_list_event_instances_requires_exactly_one_scope(
    ao_id: int | None, region_id: int | None
) -> None:
    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"),
        transport=httpx.MockTransport(lambda _: httpx.Response(500)),
    ) as client:
        with pytest.raises(ValueError, match="exactly one"):
            await client.list_event_instances(
                ao_id=ao_id,
                region_id=region_id,
                start_date=date(2026, 9, 1),
                end_date=date(2026, 9, 30),
            )
