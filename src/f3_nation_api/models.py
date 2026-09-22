"""Immutable domain models returned by the F3 Nation API."""

from dataclasses import dataclass
from datetime import date
from typing import Any

from .errors import F3NationResponseError


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise F3NationResponseError(f"{field} must be an object")
    return value


def _integer(data: dict[str, Any], key: str, field: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise F3NationResponseError(f"{field} must be an integer")
    return value


def _boolean(data: dict[str, Any], key: str, field: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise F3NationResponseError(f"{field} must be a boolean")
    return value


def _optional_string(data: dict[str, Any], key: str, field: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise F3NationResponseError(f"{field} must be a string or null")
    return value


@dataclass(frozen=True, slots=True)
class AO:
    id: int
    name: str | None
    region_id: int
    region_name: str | None = None

    @classmethod
    def from_dict(cls, value: object) -> "AO":
        data = _mapping(value, "AO")
        return cls(
            id=_integer(data, "id", "AO.id"),
            name=_optional_string(data, "name", "AO.name"),
            region_id=_integer(data, "regionId", "AO.regionId"),
            region_name=_optional_string(data, "regionName", "AO.regionName"),
        )


@dataclass(frozen=True, slots=True)
class EventInstance:
    id: int
    name: str | None
    org_id: int
    start_date: date
    is_active: bool

    @classmethod
    def from_dict(cls, value: object) -> "EventInstance":
        data = _mapping(value, "EventInstance")
        raw_date = data.get("startDate")
        if not isinstance(raw_date, str):
            raise F3NationResponseError("EventInstance.startDate must be a string")
        try:
            start_date = date.fromisoformat(raw_date)
        except ValueError as error:
            raise F3NationResponseError("EventInstance.startDate must be an ISO date") from error
        return cls(
            id=_integer(data, "id", "EventInstance.id"),
            name=_optional_string(data, "name", "EventInstance.name"),
            org_id=_integer(data, "orgId", "EventInstance.orgId"),
            start_date=start_date,
            is_active=_boolean(data, "isActive", "EventInstance.isActive"),
        )


@dataclass(frozen=True, slots=True)
class AttendanceUser:
    id: int
    f3_name: str | None

    @classmethod
    def from_dict(cls, value: object) -> "AttendanceUser":
        data = _mapping(value, "AttendanceUser")
        return cls(
            id=_integer(data, "id", "AttendanceUser.id"),
            f3_name=_optional_string(data, "f3Name", "AttendanceUser.f3Name"),
        )


@dataclass(frozen=True, slots=True)
class AttendanceType:
    id: int
    name: str

    @classmethod
    def from_dict(cls, value: object) -> "AttendanceType":
        data = _mapping(value, "AttendanceType")
        name = data.get("type")
        if not isinstance(name, str):
            raise F3NationResponseError("AttendanceType.type must be a string")
        return cls(id=_integer(data, "id", "AttendanceType.id"), name=name)


@dataclass(frozen=True, slots=True)
class AttendanceRecord:
    id: int
    user_id: int
    event_instance_id: int
    is_planned: bool
    user: AttendanceUser | None
    types: tuple[AttendanceType, ...]

    @classmethod
    def from_dict(cls, value: object) -> "AttendanceRecord":
        data = _mapping(value, "AttendanceRecord")
        raw_types = data.get("attendanceTypes")
        if not isinstance(raw_types, list):
            raise F3NationResponseError("AttendanceRecord.attendanceTypes must be an array")
        raw_user = data.get("user")
        return cls(
            id=_integer(data, "id", "AttendanceRecord.id"),
            user_id=_integer(data, "userId", "AttendanceRecord.userId"),
            event_instance_id=_integer(data, "eventInstanceId", "AttendanceRecord.eventInstanceId"),
            is_planned=_boolean(data, "isPlanned", "AttendanceRecord.isPlanned"),
            user=None if raw_user is None else AttendanceUser.from_dict(raw_user),
            types=tuple(AttendanceType.from_dict(item) for item in raw_types),
        )
