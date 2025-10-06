## Anime Service API

Servicio FastAPI para monitorear torrents basados en AniList.

### Requisitos previos

- [uv](https://docs.astral.sh/uv/) instalado
- Python 3.11 o superior
- MongoDB accesible según la configuración de `app.core.config`

### Entorno local

Instala dependencias y ejecuta la API usando la CLI oficial de FastAPI:


```powershell
uv sync
uv run fastapi run app/main.py --host 0.0.0.0 --port 8000
```

La API quedará disponible en `http://127.0.0.1:8000` con documentación interactiva en `/docs`.

### Variables de entorno

Configura estas variables para habilitar la metadata externa opcional:

- `TVDB_API_KEY`: clave de acceso para [TheTVDB](https://thetvdb.com/).
- `TMDB_API_KEY`: clave de acceso para [The Movie Database](https://www.themoviedb.org/).

Si no las defines, la API seguirá operando pero las respuestas no incluirán datos enriquecidos de estos catálogos.

Cuando están configuradas, las respuestas de `/settings` expondrán `tvdb_metadata` y `tmdb_metadata` con información como nombre oficial, año y datos de temporada.

### Docker

Construye la imagen con uv y FastAPI integrados:

```powershell
docker build -t anime-service-backend .
docker run --rm -p 8000:8000 anime-service-backend
```

### Docker Compose

Para levantar sólo el backend:

```powershell
docker compose up --build
```

### Pruebas

```powershell
uv run pytest
```
