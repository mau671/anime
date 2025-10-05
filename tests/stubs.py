from __future__ import annotations


class StubLogger:
    def bind(self, **_: object) -> StubLogger:
        return self

    def info(self, *args: object, **kwargs: object) -> None:  # noqa: D401
        """No-op info logger."""

    def warning(self, *args: object, **kwargs: object) -> None:  # noqa: D401
        """No-op warning logger."""

    def error(self, *args: object, **kwargs: object) -> None:  # noqa: D401
        """No-op error logger."""

    def debug(self, *args: object, **kwargs: object) -> None:  # noqa: D401
        """No-op debug logger."""
