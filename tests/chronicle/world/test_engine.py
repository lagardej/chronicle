"""Tests for world engine initialisation."""

from collections.abc import Generator
from pathlib import Path

import pytest

from chronicle.world.engine import init_engine


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Temporary database path."""
    return tmp_path / "game_save.db"


@pytest.fixture()
def engine(db_path: Path) -> Generator[tuple]:
    """Initialised engine pair."""
    sqlite_con, duck_con = init_engine(db_path)
    yield sqlite_con, duck_con
    sqlite_con.close()
    duck_con.close()


@pytest.mark.unit()
def test_init_engine_returns_connections(db_path: Path) -> None:
    sqlite_con, duck_con = init_engine(db_path)
    try:
        assert sqlite_con is not None
        assert duck_con is not None
    finally:
        sqlite_con.close()
        duck_con.close()


@pytest.mark.unit()
def test_init_engine_creates_schema(engine: tuple) -> None:
    sqlite_con, _ = engine

    rows = sqlite_con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    assert {r[0] for r in rows} == {
        "cells",
        "adjacency",
        "sites",
        "paths",
        "path_segments",
        "sphere_geometry",
        "ring_geometry",
    }


@pytest.mark.unit()
def test_init_engine_enables_wal(engine: tuple) -> None:
    sqlite_con, _ = engine

    mode = sqlite_con.execute("PRAGMA journal_mode;").fetchone()[0]

    assert mode == "wal"


@pytest.mark.unit()
def test_init_engine_creates_db_file(db_path: Path) -> None:
    sqlite_con, duck_con = init_engine(db_path)
    sqlite_con.close()
    duck_con.close()

    assert db_path.exists()
