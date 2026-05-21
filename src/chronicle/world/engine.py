"""World engine initialisation."""

import sqlite3
from pathlib import Path

import duckdb

from chronicle.world.schema import init_schema

__all__ = ["init_engine"]


def init_engine(
    save_path: Path,
) -> tuple[sqlite3.Connection, duckdb.DuckDBPyConnection]:
    """Initialise the world engine and return the database connection pair.

    Creates the SQLite save file and schema if they do not already exist.
    DuckDB is opened in-memory as a read-only compute layer over SQLite.

    Args:
        save_path: Path to the SQLite save file (created if absent).

    Returns:
        A (sqlite_con, duck_con) tuple. Caller owns both connection lifecycles.
    """
    sqlite_con = _open_sqlite(save_path)
    duck_con = _open_duckdb()
    return sqlite_con, duck_con


def _open_sqlite(save_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(save_path)
    con.execute("PRAGMA journal_mode=WAL;")
    init_schema(con)
    return con


def _open_duckdb() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("INSTALL sqlite; LOAD sqlite;")
    return con
