"""Tests for LOD 2 cell instantiation."""

import sqlite3
from collections.abc import Generator

import h3
import pytest

from chronicle.world.cells import ensure_lod2_cell
from chronicle.world.schema import init_schema

# H3 resolution used for LOD 2 in the POC
_LOD2_RES = 6


@pytest.fixture()
def con() -> Generator[sqlite3.Connection]:
    """In-memory SQLite connection with schema."""
    con = sqlite3.connect(":memory:")
    init_schema(con)
    yield con
    con.close()


def _cell_exists(con: sqlite3.Connection, cell_index: int) -> bool:
    row = con.execute(
        "SELECT 1 FROM cells WHERE cell_index = ?", (cell_index,)
    ).fetchone()
    return row is not None


def _adjacency_count(con: sqlite3.Connection, cell_index: int) -> int:
    row = con.execute(
        "SELECT COUNT(*) FROM adjacency WHERE origin_index = ?", (cell_index,)
    ).fetchone()
    return row[0]


@pytest.mark.unit()
def test_ensure_lod2_cell_inserts_cell(con: sqlite3.Connection) -> None:
    cell_index = h3.latlng_to_cell(51.5, -0.1, _LOD2_RES)

    ensure_lod2_cell(con, cell_index)

    assert _cell_exists(con, cell_index)


@pytest.mark.unit()
def test_ensure_lod2_cell_inserts_six_adjacency_edges(con: sqlite3.Connection) -> None:
    cell_index = h3.latlng_to_cell(51.5, -0.1, _LOD2_RES)

    ensure_lod2_cell(con, cell_index)

    assert _adjacency_count(con, cell_index) == 6


@pytest.mark.unit()
def test_ensure_lod2_cell_is_idempotent(con: sqlite3.Connection) -> None:
    cell_index = h3.latlng_to_cell(51.5, -0.1, _LOD2_RES)

    ensure_lod2_cell(con, cell_index)
    ensure_lod2_cell(con, cell_index)

    assert _cell_exists(con, cell_index)
    assert _adjacency_count(con, cell_index) == 6


@pytest.mark.unit()
def test_ensure_lod2_cell_sets_lod_level(con: sqlite3.Connection) -> None:
    cell_index = h3.latlng_to_cell(51.5, -0.1, _LOD2_RES)

    ensure_lod2_cell(con, cell_index)

    row = con.execute(
        "SELECT lod_level FROM cells WHERE cell_index = ?", (cell_index,)
    ).fetchone()
    assert row[0] == 2
