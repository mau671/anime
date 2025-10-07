from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

TemplateContext = dict[str, Any]


def build_base_context(now: datetime | None = None) -> TemplateContext:
    moment = now or datetime.now(UTC)
    return {
        "currentYear": moment.year,
        "currentMonth": f"{moment.month:02d}",
        "currentDay": f"{moment.day:02d}",
    }


def render_template(template: str, context: TemplateContext) -> str:
    result = template
    for key, value in context.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                result = result.replace(f"{{{key}.{sub_key}}}", str(sub_value))
        else:
            result = result.replace(f"{{{key}}}", str(value))
    return result
