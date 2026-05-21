"""LOD 2 cell instantiation for the world engine."""

import sqlite3

import h3

__all__ = ["ensure_lod2_cell"]

_LOD2_LEVEL = 2


def ensure_lod2_cell(con: sqlite3.Connection, cell_index: str) -> None:
    """Ensure a LOD 2 cell and its 6 adjacency edges exist in SQLite.

    Creates the cell row and adjacency edges if absent. Safe to call
    multiple times — existing rows are left unchanged.

    Args:
        con: An open SQLite connection with the world schema initialised.
        cell_index: H3 cell index at LOD 2 resolution.
    """
    _insert_cell(con, cell_index)
    _insert_adjacency(con, cell_index)


def _insert_cell(con: sqlite3.Connection, cell_index: str) -> None:
    con.execute(
        """
        INSERT OR IGNORE INTO cells (cell_index, lod_level)
        VALUES (?, ?)
        """,
        (cell_index, _LOD2_LEVEL),
    )


def _insert_adjacency(con: sqlite3.Connection, cell_index: str) -> None:
    neighbors = set(h3.grid_disk(cell_index, 1)) - {cell_index}
    distance = _edge_distance_km(cell_index)
    con.executemany(
        """
        INSERT OR IGNORE INTO adjacency
            (origin_index, neighbor_index, lod_level, distance)
        VALUES (?, ?, ?, ?)
        """,
        [(cell_index, n, _LOD2_LEVEL, distance) for n in neighbors],
    )


def _edge_distance_km(cell_index: str) -> float:
    return h3.average_hexagon_edge_length(h3.get_resolution(cell_index), unit="km")
