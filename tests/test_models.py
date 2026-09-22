from datetime import date

import pytest

from f3_nation_api.errors import F3NationResponseError
from f3_nation_api.models import AO, AttendanceRecord, EventInstance


def test_ao_parses_documented_payload() -> None:
    ao = AO.from_dict(
        {
            "id": 42,
            "name": "Hiawatha",
            "regionId": 7,
            "regionName": "Puget Sound",
            "locationId": 9,
            "latitude": 47.6,
            "longitude": -122.3,
            "eventCount": 2,
        }
    )

    assert ao.id == 42
    assert ao.name == "Hiawatha"
    assert ao.region_id == 7


def test_event_instance_parses_relevant_fields() -> None:
    event = EventInstance.from_dict(
        {
            "id": 101,
            "name": "Hiawatha - Bootcamp",
            "isActive": True,
            "orgId": 42,
            "startDate": "2026-09-20",
        }
    )

    assert event.id == 101
    assert event.org_id == 42
    assert event.start_date == date(2026, 9, 20)


def test_attendance_record_parses_nested_user_and_types() -> None:
    attendance = AttendanceRecord.from_dict(
        {
            "id": 12,
            "userId": 88,
            "eventInstanceId": 101,
            "isPlanned": False,
            "user": {"id": 88, "f3Name": "Comeback"},
            "attendanceTypes": [{"id": 1, "type": "PAX"}],
        }
    )

    assert attendance.user is not None
    assert attendance.user.f3_name == "Comeback"
    assert attendance.types[0].name == "PAX"


def test_models_reject_wrong_field_types() -> None:
    with pytest.raises(F3NationResponseError, match="AO.id"):
        AO.from_dict({"id": "42", "name": "Hiawatha", "regionId": 7})
