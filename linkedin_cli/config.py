"""Configuration loading and normalization for linkedin-cli."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml

from linkedin_cli.constants import DEFAULT_BROWSER
from linkedin_cli.constants import DEFAULT_CONFIG_FILE_NAMES
from linkedin_cli.constants import DEFAULT_FETCH_COUNT
from linkedin_cli.constants import DEFAULT_FILTER_MODE
from linkedin_cli.constants import DEFAULT_MAX_RETRIES
from linkedin_cli.constants import DEFAULT_REQUEST_DELAY
from linkedin_cli.constants import DEFAULT_RETRY_BASE_DELAY
from linkedin_cli.constants import DEFAULT_TIMEOUT
from linkedin_cli.constants import DEFAULT_WRITE_DELAY_MAX
from linkedin_cli.constants import DEFAULT_WRITE_DELAY_MIN
from linkedin_cli.constants import ENV_BROWSER
from linkedin_cli.constants import ENV_CONFIG_PATH
from linkedin_cli.constants import ENV_HEADLESS
from linkedin_cli.constants import ENV_PROXY
from linkedin_cli.constants import SUPPORTED_BROWSERS


def _to_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _to_int(value: Any, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _to_float(value: Any, default: float) -> float:
    if value is None:
        return default
    return float(value)


def _get_value(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _normalize_browser_name(value: Any) -> str:
    browser = str(value or DEFAULT_BROWSER).strip().lower()
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(
            f"Unsupported browser '{browser}'. Expected one of: {', '.join(SUPPORTED_BROWSERS)}"
        )
    return browser


@dataclass
class FetchConfig:
    count: int = DEFAULT_FETCH_COUNT


@dataclass
class FilterConfig:
    enabled: bool = False
    mode: str = DEFAULT_FILTER_MODE


@dataclass
class BrowserConfig:
    preferred: str = DEFAULT_BROWSER
    fallback_enabled: bool = True
    headless: bool = True


@dataclass
class RateLimitConfig:
    request_delay: float = DEFAULT_REQUEST_DELAY
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY
    write_delay_min: float = DEFAULT_WRITE_DELAY_MIN
    write_delay_max: float = DEFAULT_WRITE_DELAY_MAX
    timeout: float = DEFAULT_TIMEOUT


@dataclass
class RuntimeConfig:
    proxy: str | None = None


@dataclass
class AppConfig:
    fetch: FetchConfig
    filter: FilterConfig
    browser: BrowserConfig
    rate_limit: RateLimitConfig
    runtime: RuntimeConfig
    path: Path | None = None


def resolve_config_path(cwd: Path | None = None) -> Path | None:
    env_path = os.getenv(ENV_CONFIG_PATH)
    if env_path:
        path = Path(env_path).expanduser()
        return path if path.exists() else None

    search_root = cwd or Path.cwd()
    for name in DEFAULT_CONFIG_FILE_NAMES:
        path = search_root / name
        if path.exists():
            return path
    return None


def load_raw_config(path: Path | None = None) -> tuple[dict[str, Any], Path | None]:
    resolved_path = path or resolve_config_path()
    if resolved_path is None:
        return {}, None

    with resolved_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Config file must contain a mapping: {resolved_path}")
        return data, resolved_path


def load_config(path: Path | None = None) -> AppConfig:
    raw, resolved_path = load_raw_config(path)

    fetch_raw = raw.get("fetch", {})
    filter_raw = raw.get("filter", {})
    browser_raw = raw.get("browser", {})
    rate_limit_raw = raw.get("rate_limit") or raw.get("rateLimit") or {}

    fetch = FetchConfig(
        count=_to_int(_get_value(fetch_raw, "count"), DEFAULT_FETCH_COUNT),
    )
    filter_config = FilterConfig(
        enabled=_to_bool(_get_value(filter_raw, "enabled"), False),
        mode=str(_get_value(filter_raw, "mode") or DEFAULT_FILTER_MODE),
    )
    browser = BrowserConfig(
        preferred=_normalize_browser_name(
            os.getenv(ENV_BROWSER) or _get_value(browser_raw, "preferred")
        ),
        fallback_enabled=_to_bool(
            _get_value(browser_raw, "fallback_enabled", "fallbackEnabled"),
            True,
        ),
        headless=_to_bool(os.getenv(ENV_HEADLESS), _to_bool(_get_value(browser_raw, "headless"), True)),
    )
    rate_limit = RateLimitConfig(
        request_delay=_to_float(
            _get_value(rate_limit_raw, "request_delay", "requestDelay"),
            DEFAULT_REQUEST_DELAY,
        ),
        max_retries=_to_int(
            _get_value(rate_limit_raw, "max_retries", "maxRetries"),
            DEFAULT_MAX_RETRIES,
        ),
        retry_base_delay=_to_float(
            _get_value(rate_limit_raw, "retry_base_delay", "retryBaseDelay"),
            DEFAULT_RETRY_BASE_DELAY,
        ),
        write_delay_min=_to_float(
            _get_value(rate_limit_raw, "write_delay_min", "writeDelayMin"),
            DEFAULT_WRITE_DELAY_MIN,
        ),
        write_delay_max=_to_float(
            _get_value(rate_limit_raw, "write_delay_max", "writeDelayMax"),
            DEFAULT_WRITE_DELAY_MAX,
        ),
        timeout=_to_float(_get_value(rate_limit_raw, "timeout"), DEFAULT_TIMEOUT),
    )
    runtime = RuntimeConfig(proxy=os.getenv(ENV_PROXY))

    return AppConfig(
        fetch=fetch,
        filter=filter_config,
        browser=browser,
        rate_limit=rate_limit,
        runtime=runtime,
        path=resolved_path,
    )
