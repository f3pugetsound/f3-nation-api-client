"""Asynchronous HTTP client for the F3 Nation API."""

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any, Self

import httpx

from .errors import (
    F3NationAmbiguousMatchError,
    F3NationAuthenticationError,
    F3NationNotFoundError,
    F3NationRateLimitError,
    F3NationResponseError,
    F3NationServerError,
)
from .models import AO, AttendanceRecord, EventInstance


@dataclass(frozen=True, slots=True)
class F3NationClientConfig:
    """Connection and bounded-retry settings."""

    api_key: str
    client_name: str
    base_url: str = "https://api.f3nation.com"
    timeout: float = 10.0
    max_retries: int = 2
    retry_base_delay: float = 0.25
    max_retry_delay: float = 5.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("api_key must not be empty")
        if not self.client_name.strip():
            raise ValueError("client_name must not be empty")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if self.retry_base_delay < 0 or self.max_retry_delay < 0:
            raise ValueError("retry delays must not be negative")


class F3NationClient:
    """Typed async client with credential-safe transport failures."""

    def __init__(
        self,
        config: F3NationClientConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            base_url=self._config.base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Client": self._config.client_name,
                "Accept": "application/json",
            },
            timeout=self._config.timeout,
            transport=self._transport,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_json(
        self, path: str, *, params: dict[str, str | int | bool] | None = None
    ) -> dict[str, Any]:
        """GET a JSON object, retrying only transient failures."""
        if self._client is None:
            raise RuntimeError("F3NationClient must be used as an async context manager")

        response: httpx.Response | None = None
        for attempt in range(self._config.max_retries + 1):
            try:
                response = await self._client.get(path, params=params)
            except httpx.RequestError as error:
                if attempt == self._config.max_retries:
                    raise F3NationServerError("F3 Nation API network request failed") from error
                await asyncio.sleep(self._retry_delay(attempt, None))
                continue

            if response.status_code in {401, 403}:
                raise F3NationAuthenticationError(
                    f"F3 Nation API authentication failed (HTTP {response.status_code})"
                )
            if response.status_code == 429:
                if attempt == self._config.max_retries:
                    raise F3NationRateLimitError("F3 Nation API rate limit retries exhausted")
                await asyncio.sleep(self._retry_delay(attempt, response))
                continue
            if response.status_code >= 500:
                if attempt == self._config.max_retries:
                    raise F3NationServerError(
                        f"F3 Nation API unavailable (HTTP {response.status_code})"
                    )
                await asyncio.sleep(self._retry_delay(attempt, response))
                continue
            if response.status_code >= 400:
                raise F3NationResponseError(
                    f"F3 Nation API request failed (HTTP {response.status_code})"
                )
            break

        if response is None:  # pragma: no cover - loop always requests at least once
            raise F3NationServerError("F3 Nation API request failed")

        try:
            payload = response.json()
        except ValueError as error:
            raise F3NationResponseError("F3 Nation API returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise F3NationResponseError("F3 Nation API response must be a JSON object")
        return payload

    async def search_aos(self, search_term: str) -> tuple[AO, ...]:
        """Return active AOs matching a name search term."""
        term = search_term.strip()
        if len(term) < 2:
            raise ValueError("search_term must contain at least two characters")
        payload = await self.get_json("/v1/org-chart/aos", params={"searchTerm": term})
        raw_aos = payload.get("aos")
        if not isinstance(raw_aos, list):
            raise F3NationResponseError("F3 Nation AO response must contain an aos array")
        return tuple(AO.from_dict(item) for item in raw_aos)

    async def find_ao_exact(self, name: str, *, region_id: int) -> AO:
        """Find exactly one AO by normalized name within a region."""
        normalized_name = name.strip().casefold()
        matches = tuple(
            ao
            for ao in await self.search_aos(name)
            if ao.region_id == region_id
            and ao.name is not None
            and ao.name.strip().casefold() == normalized_name
        )
        if not matches:
            raise F3NationNotFoundError(
                f"No AO named {name.strip()!r} exists in region {region_id}"
            )
        if len(matches) > 1:
            raise F3NationAmbiguousMatchError(
                f"Multiple AOs named {name.strip()!r} exist in region {region_id}"
            )
        return matches[0]

    async def list_event_instances(
        self,
        *,
        ao_id: int,
        start_date: date,
        end_date: date,
        page_size: int = 100,
    ) -> tuple[EventInstance, ...]:
        """Return every active AO event instance in an inclusive date range."""
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        if page_size <= 0:
            raise ValueError("page_size must be positive")

        events: list[EventInstance] = []
        page_index = 0
        while True:
            payload = await self.get_json(
                "/v1/event-instance",
                params={
                    "aoOrgId": ao_id,
                    "startDate": start_date.isoformat(),
                    "startDateTo": end_date.isoformat(),
                    "pageIndex": page_index,
                    "pageSize": page_size,
                },
            )
            raw_events = payload.get("eventInstances")
            total_count = payload.get("totalCount")
            if not isinstance(raw_events, list):
                raise F3NationResponseError(
                    "F3 Nation event response must contain an eventInstances array"
                )
            if not isinstance(total_count, int) or isinstance(total_count, bool) or total_count < 0:
                raise F3NationResponseError(
                    "F3 Nation event response must contain a non-negative totalCount"
                )
            page = tuple(EventInstance.from_dict(item) for item in raw_events)
            events.extend(page)
            if len(events) >= total_count:
                return tuple(events)
            if not page:
                raise F3NationResponseError("F3 Nation event pagination ended before totalCount")
            page_index += 1

    async def get_attendance(
        self, *, event_instance_id: int, planned: bool = True
    ) -> tuple[AttendanceRecord, ...]:
        """Return planned or actual attendance for one event instance."""
        payload = await self.get_json(
            f"/v1/attendance/event-instance/{event_instance_id}",
            params={"isPlanned": planned},
        )
        raw_attendance = payload.get("attendance")
        if not isinstance(raw_attendance, list):
            raise F3NationResponseError(
                "F3 Nation attendance response must contain an attendance array"
            )
        return tuple(AttendanceRecord.from_dict(item) for item in raw_attendance)

    def _retry_delay(self, attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    delay = float(str(retry_after))
                    return min(max(delay, 0.0), self._config.max_retry_delay)
                except ValueError:
                    pass
        delay = self._config.retry_base_delay * float(2**attempt)
        return min(delay, self._config.max_retry_delay)
