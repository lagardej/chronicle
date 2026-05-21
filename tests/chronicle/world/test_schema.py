"""Tests for world engine schema initialisation."""

import sqlite3
from collections.abc import Generator

import pytest

from chronicle.world.schema import init_schema


@pytest.fixture()
def con() -> Generator[sqlite3.Connection]:
    """In-memory SQLite connection."""
    con = sqlite3.connect(":memory:")
    yield con
    con.close()


def _tables(con: sqlite3.Connection) -> set[str]:
    rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


def _columns(con: sqlite3.Connection, table: str) -> set[str]:
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()  # noqa: S608
    return {r[1] for r in rows}


@pytest.mark.unit()
def test_init_schema_creates_all_tables(con: sqlite3.Connection) -> None:
    init_schema(con)

    assert _tables(con) == {
        "cells",
        "adjacency",
        "sites",
        "paths",
        "path_segments",
        "sphere_geometry",
        "ring_geometry",
    }


@pytest.mark.unit()
def test_cells_columns(con: sqlite3.Connection) -> None:
    init_schema(con)

    assert _columns(con, "cells") == {
        "cell_index",
        "lod_level",
        "elevation",
        "crust_thickness",
        "water_table",
        "precipitation",
        "current_temperature",
        "biomass",
        "soil_fertility",
        "current_mud_factor",
    }


@pytest.mark.unit()
def test_adjacency_columns(con: sqlite3.Connection) -> None:
    init_schema(con)

    assert _columns(con, "adjacency") == {
        "origin_index",
        "neighbor_index",
        "lod_level",
        "distance",
        "flux_coefficient",
    }


@pytest.mark.unit()
def test_init_schema_is_idempotent(con: sqlite3.Connection) -> None:
    init_schema(con)
    init_schema(con)

    assert _tables(con) == {
        "cells",
        "adjacency",
        "sites",
        "paths",
        "path_segments",
        "sphere_geometry",
        "ring_geometry",
    }
