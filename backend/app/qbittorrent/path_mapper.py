from __future__ import annotations

from pathlib import Path


class PathMapper:
    """
    Maps paths between backend and qBittorrent.

    Example:
        Backend:     /storage/data/torrents/shows/Anime/Season 1
        qBittorrent: /data/torrents/shows/Anime/Season 1

        Mapping: {"from": "/storage/data/torrents", "to": "/data/torrents"}
    """

    def __init__(self, mappings: list[dict[str, str]]) -> None:
        """
        Initialize path mapper with mappings.

        Args:
            mappings: List of mappings like [{"from": "/backend/path", "to": "/qbit/path"}]
        """
        self._mappings: list[tuple[Path, Path]] = []

        for mapping in mappings:
            from_path = Path(mapping.get("from", ""))
            to_path = Path(mapping.get("to", ""))
            if from_path and to_path:
                self._mappings.append((from_path, to_path))

        # Sort mappings by path length (longest first) to match most specific paths first
        self._mappings.sort(key=lambda x: len(str(x[0])), reverse=True)

    def to_qbittorrent(self, backend_path: Path | str) -> Path:
        """
        Convert a backend path to qBittorrent path.

        Args:
            backend_path: Path used by the backend

        Returns:
            Path that qBittorrent should use
        """
        path = Path(backend_path)

        for from_path, to_path in self._mappings:
            try:
                # Check if the path starts with the mapping's from_path
                relative = path.relative_to(from_path)
                # Map to qBittorrent path
                return to_path / relative
            except ValueError:
                # Path doesn't start with this mapping, try next one
                continue

        # No mapping found, return original path
        return path

    def to_backend(self, qbit_path: Path | str) -> Path:
        """
        Convert a qBittorrent path to backend path.

        Args:
            qbit_path: Path used by qBittorrent

        Returns:
            Path that the backend should use
        """
        path = Path(qbit_path)

        for from_path, to_path in self._mappings:
            try:
                # Check if the path starts with the mapping's to_path
                relative = path.relative_to(to_path)
                # Map to backend path
                return from_path / relative
            except ValueError:
                # Path doesn't start with this mapping, try next one
                continue

        # No mapping found, return original path
        return path
