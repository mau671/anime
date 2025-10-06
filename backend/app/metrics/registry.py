from __future__ import annotations

from threading import Lock

from prometheus_client import Counter, Histogram, start_http_server

ANILIST_UPSERTED = Counter(
    "anilist_upserted_items", "Number of anime records upserted from AniList"
)
NYAA_ITEMS_FOUND = Counter(
    "nyaa_items_found", "Number of candidate torrent items found", ["anilist_id"]
)
TORRENTS_DOWNLOADED = Counter(
    "nyaa_torrents_downloaded", "Number of torrents downloaded", ["anilist_id"]
)
TORRENTS_ERRORS = Counter(
    "nyaa_torrents_errors", "Number of torrent download errors", ["anilist_id"]
)
REQUEST_LATENCY = Histogram(
    "external_request_latency_seconds", "Latency of external HTTP requests", ["target"]
)

_METRICS_LOCK = Lock()
_METRICS_STARTED = False


def start_metrics_server(host: str, port: int) -> None:
    global _METRICS_STARTED
    with _METRICS_LOCK:
        if _METRICS_STARTED:
            return
        start_http_server(port, addr=host)
        _METRICS_STARTED = True
