from __future__ import annotations

import asyncio
import os
import re
import tempfile
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from structlog.stdlib import BoundLogger

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')
MULTIPLE_SPACES = re.compile(r"\s+")
RESOLUTION_PATTERN = re.compile(r"\b(480p|720p|960p|1080p|1440p|2160p|4K)\b", re.IGNORECASE)
SUBGROUP_PATTERN = re.compile(r"\[([^\]]+)\]")
INFOHASH_PATTERN = re.compile(r"([a-fA-F0-9]{40})")


def sanitize_filename(title: str) -> str:
    cleaned = INVALID_FILENAME_CHARS.sub(" ", title)
    cleaned = cleaned.replace("..", ".")
    cleaned = MULTIPLE_SPACES.sub(" ", cleaned)
    return cleaned.strip()


def sanitize_save_path(base_path: Path) -> Path:
    return base_path.expanduser().resolve()


def _flatten_context(prefix: str, value: object, *, sanitize_values: bool) -> dict[str, str]:
    flattened: dict[str, str] = {}
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if nested_value is None:
                continue
            nested_key = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(
                _flatten_context(nested_key, nested_value, sanitize_values=sanitize_values)
            )
    elif isinstance(value, (list, tuple, set)):
        items = [str(item) for item in value if item is not None]
        if sanitize_values:
            items = [sanitize_filename(item) for item in items]
        flattened[prefix] = ", ".join(items)
    elif value is not None:
        text = str(value)
        flattened[prefix] = sanitize_filename(text) if sanitize_values else text
    return flattened


def build_template_mapping(
    context: Mapping[str, object | None], *, sanitize_values: bool = False
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for key, value in context.items():
        if value is None:
            continue
        key_str = str(key)
        mapping.update(_flatten_context(key_str, value, sanitize_values=sanitize_values))
    return mapping


def render_save_path_template(template: str, mapping: Mapping[str, object | None]) -> str:
    flattened = build_template_mapping(mapping, sanitize_values=True)

    def replacement(match: re.Match[str]) -> str:
        placeholder = match.group(1)
        if not placeholder:
            return match.group(0)
        value = flattened.get(placeholder, "")
        return value

    pattern = re.compile(r"\{\s*([^{}\s]+)\s*\}")
    rendered = pattern.sub(replacement, template)
    cleaned = MULTIPLE_SPACES.sub(" ", rendered)
    return cleaned.strip()


def ensure_directory(path: Path, create: bool, logger: BoundLogger | None = None) -> None:
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"Path {path} exists and is not a directory")
        return

    if create:
        path.mkdir(parents=True, exist_ok=True)
        if logger:
            logger.info("directory_created", path=str(path))
    else:
        raise FileNotFoundError(f"Directory {path} does not exist")


async def write_bytes_atomically(filepath: Path, data: bytes) -> None:
    loop = asyncio.get_running_loop()

    def _write() -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=str(filepath.parent), delete=False) as tmp:
            tmp.write(data)
            temp_name = tmp.name
        os.replace(temp_name, filepath)

    await loop.run_in_executor(None, _write)


def extract_resolution(text: str) -> str | None:
    match = RESOLUTION_PATTERN.search(text)
    if match:
        value = match.group(1).upper()
        return "2160P" if value in {"2160P", "4K"} else value
    return None


def extract_subgroup(text: str) -> str | None:
    match = SUBGROUP_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return None


def any_includes(text: str, includes: Iterable[str]) -> bool:
    text_lower = text.lower()
    return all(term.lower() in text_lower for term in includes)


def any_excludes(text: str, excludes: Iterable[str]) -> bool:
    text_lower = text.lower()
    return any(term.lower() in text_lower for term in excludes)


def extract_infohash(text: str) -> str | None:
    match = INFOHASH_PATTERN.search(text)
    if match:
        return match.group(1).lower()
    return None


def utc_now() -> datetime:
    return datetime.now(UTC)
