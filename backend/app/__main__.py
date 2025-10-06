from __future__ import annotations

import sys
from textwrap import dedent


def main() -> None:
    message = dedent(
        """
        anime-service ya no expone una interfaz de línea de comandos.
        Usa el comando recomendado de FastAPI:

            uv run fastapi run app/main.py --host 0.0.0.0 --port 8000
        """
    ).strip()
    print(message, file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
