from __future__ import annotations

"""
Service-to-service API keys.

Keys come from the SERVICE_API_KEYS env var (comma-separated). The "dev-key"
default exists for local development only — set real keys in any deployed
environment and register them as Kong consumers on key-auth routes.
"""

import os
from typing import Set


def get_service_api_keys() -> Set[str]:
    raw = os.getenv("SERVICE_API_KEYS", "dev-key")
    return {k.strip() for k in raw.split(",") if k.strip()}


def is_valid_service_key(key: str | None) -> bool:
    return key is not None and key in get_service_api_keys()
