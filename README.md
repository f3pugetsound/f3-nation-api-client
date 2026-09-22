# F3 Nation API Client

Typed async Python client for the [F3 Nation API](https://api.f3nation.com/docs).

## Installation

Pin a tagged release:

```toml
[project]
dependencies = [
  "f3-nation-api-client @ git+https://github.com/f3pugetsound/f3-nation-api-client.git@v0.1.0",
]
```

## Usage

```python
from datetime import date

from f3_nation_api import F3NationClient, F3NationClientConfig

config = F3NationClientConfig(
    api_key="...",
    client_name="my-f3-application",
)

async with F3NationClient(config) as client:
    ao = await client.find_ao_exact("Hiawatha", region_id=123)
    events = await client.list_event_instances(
        ao_id=ao.id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 4, 30),
    )
    attendance = await client.get_attendance(
        event_instance_id=events[0].id,
        planned=False,
    )
```

Requests include the API's required `Authorization: Bearer ...` and `Client` headers. Transient network errors, rate limits, and server errors use bounded retries. Exceptions never include response bodies or credentials.

## Development

```bash
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```
