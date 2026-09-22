import httpx
import pytest

from f3_nation_api import F3NationClient, F3NationClientConfig


@pytest.mark.asyncio
@pytest.mark.parametrize(("planned", "encoded"), [(True, "true"), (False, "false")])
async def test_get_attendance_selects_planned_or_actual(planned: bool, encoded: str) -> None:
    captured: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request
        return httpx.Response(
            200,
            json={
                "attendance": [
                    {
                        "id": 12,
                        "userId": 88,
                        "eventInstanceId": 101,
                        "isPlanned": planned,
                        "user": {"id": 88, "f3Name": "Comeback"},
                        "attendanceTypes": [{"id": 1, "type": "PAX"}],
                    }
                ]
            },
        )

    async with F3NationClient(
        F3NationClientConfig(api_key="key", client_name="test"),
        transport=httpx.MockTransport(handler),
    ) as client:
        attendance = await client.get_attendance(event_instance_id=101, planned=planned)

    assert attendance[0].user is not None
    assert attendance[0].user.f3_name == "Comeback"
    assert captured is not None
    assert captured.url.path == "/v1/attendance/event-instance/101"
    assert captured.url.params["isPlanned"] == encoded
