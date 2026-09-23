"""Typed async client for the F3 Nation API."""

from .client import F3NationClient, F3NationClientConfig
from .errors import (
    F3NationAmbiguousMatchError,
    F3NationAuthenticationError,
    F3NationError,
    F3NationNotFoundError,
    F3NationRateLimitError,
    F3NationResponseError,
    F3NationServerError,
)
from .models import (
    AO,
    AttendanceRecord,
    AttendanceType,
    AttendanceUser,
    EventInstance,
    RegionAO,
)

__all__ = [
    "AO",
    "AttendanceRecord",
    "AttendanceType",
    "AttendanceUser",
    "EventInstance",
    "RegionAO",
    "F3NationClient",
    "F3NationClientConfig",
    "F3NationAmbiguousMatchError",
    "F3NationAuthenticationError",
    "F3NationError",
    "F3NationNotFoundError",
    "F3NationRateLimitError",
    "F3NationResponseError",
    "F3NationServerError",
]
