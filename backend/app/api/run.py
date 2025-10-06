from __future__ import annotations

from textwrap import dedent


def main() -> None:
    message = dedent(
        """
        El lanzador basado en Uvicorn fue reemplazado.
        Ejecuta la aplicación con la CLI de FastAPI:

            uv run fastapi run app/main.py --host 0.0.0.0 --port 8000
        """
    ).strip()
    raise RuntimeError(message)


if __name__ == "__main__":
    main()
