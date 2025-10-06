"""Tests for path mapping between backend and qBittorrent."""

from pathlib import Path

from app.qbittorrent.path_mapper import PathMapper


def test_path_mapper_to_qbittorrent():
    """Test converting backend path to qBittorrent path."""
    mappings = [
        {"from": "/storage/data/torrents", "to": "/data/torrents"},
    ]
    mapper = PathMapper(mappings)

    backend_path = Path("/storage/data/torrents/shows/Anime/Season 1")
    qbit_path = mapper.to_qbittorrent(backend_path)

    assert qbit_path == Path("/data/torrents/shows/Anime/Season 1")


def test_path_mapper_to_backend():
    """Test converting qBittorrent path to backend path."""
    mappings = [
        {"from": "/storage/data/torrents", "to": "/data/torrents"},
    ]
    mapper = PathMapper(mappings)

    qbit_path = Path("/data/torrents/shows/Anime/Season 1")
    backend_path = mapper.to_backend(qbit_path)

    assert backend_path == Path("/storage/data/torrents/shows/Anime/Season 1")


def test_path_mapper_multiple_mappings():
    """Test path mapper with multiple mappings."""
    mappings = [
        {"from": "/storage/data/torrents", "to": "/data/torrents"},
        {"from": "/storage/media", "to": "/media"},
    ]
    mapper = PathMapper(mappings)

    # Test first mapping
    backend_path1 = Path("/storage/data/torrents/shows")
    qbit_path1 = mapper.to_qbittorrent(backend_path1)
    assert qbit_path1 == Path("/data/torrents/shows")

    # Test second mapping
    backend_path2 = Path("/storage/media/movies")
    qbit_path2 = mapper.to_qbittorrent(backend_path2)
    assert qbit_path2 == Path("/media/movies")


def test_path_mapper_no_match():
    """Test path mapper when no mapping matches."""
    mappings = [
        {"from": "/storage/data/torrents", "to": "/data/torrents"},
    ]
    mapper = PathMapper(mappings)

    # Path that doesn't match any mapping
    backend_path = Path("/other/path/somewhere")
    qbit_path = mapper.to_qbittorrent(backend_path)

    # Should return original path
    assert qbit_path == backend_path


def test_path_mapper_longest_match():
    """Test path mapper selects longest matching path."""
    mappings = [
        {"from": "/storage", "to": "/mnt"},
        {"from": "/storage/data/torrents", "to": "/data/torrents"},
    ]
    mapper = PathMapper(mappings)

    # Should use the more specific mapping
    backend_path = Path("/storage/data/torrents/shows/Anime")
    qbit_path = mapper.to_qbittorrent(backend_path)
    assert qbit_path == Path("/data/torrents/shows/Anime")


def test_path_mapper_empty_mappings():
    """Test path mapper with no mappings."""
    mapper = PathMapper([])

    backend_path = Path("/storage/data/torrents")
    qbit_path = mapper.to_qbittorrent(backend_path)

    # Should return original path
    assert qbit_path == backend_path


def test_path_mapper_windows_paths():
    """Test path mapper with Windows paths."""
    mappings = [
        {"from": "C:\\storage\\data\\torrents", "to": "/data/torrents"},
    ]
    mapper = PathMapper(mappings)

    backend_path = Path("C:/storage/data/torrents/shows/Anime")
    qbit_path = mapper.to_qbittorrent(backend_path)

    # PathLib normalizes paths
    assert str(qbit_path).replace("\\", "/") == "/data/torrents/shows/Anime"
