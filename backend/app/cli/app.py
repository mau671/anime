from __future__ import annotations

from textwrap import dedent

__all__ = ["cli"]


def cli() -> None:
    message = dedent(
        """
        La interfaz de línea de comandos fue retirada.
        Ejecuta el servicio con la CLI oficial de FastAPI:

            uv run fastapi run app/main.py --host 0.0.0.0 --port 8000
        """
    ).strip()
    raise RuntimeError(message)
