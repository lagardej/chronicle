"""World engine SQLite schema initialisation."""

import sqlite3

__all__ = ["init_schema"]

_DDL = """\
CREATE TABLE IF NOT EXISTS cells (
    cell_index          BIGINT  PRIMARY KEY,
    lod_level           INTEGER NOT NULL,
    elevation           REAL    NOT NULL DEFAULT 0.0,
    crust_thickness     REAL    NOT NULL DEFAULT 30.0,
    water_table         REAL    NOT NULL DEFAULT 0.0,
    precipitation       REAL    NOT NULL DEFAULT 0.0,
    current_temperature REAL             DEFAULT 20.0,
    biomass             REAL    NOT NULL DEFAULT 1.0,
    soil_fertility      REAL    NOT NULL DEFAULT 0.0,
    current_mud_factor  REAL             DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS adjacency (
    origin_index    BIGINT  NOT NULL,
    neighbor_index  BIGINT  NOT NULL,
    lod_level       INTEGER NOT NULL,
    distance        REAL    NOT NULL,
    flux_coefficient REAL   DEFAULT 1.0,
    PRIMARY KEY (origin_index, neighbor_index),
    FOREIGN KEY (origin_index) REFERENCES cells (cell_index)
);

CREATE TABLE IF NOT EXISTS sites (
    site_id     INTEGER PRIMARY KEY,
    cell_index  BIGINT  NOT NULL,
    site_type   TEXT    NOT NULL,
    name        TEXT    NOT NULL,
    FOREIGN KEY (cell_index) REFERENCES cells (cell_index)
);

CREATE TABLE IF NOT EXISTS paths (
    path_id             INTEGER PRIMARY KEY,
    origin_site_id      INTEGER,
    destination_site_id INTEGER,
    name                TEXT,
    FOREIGN KEY (origin_site_id)      REFERENCES sites (site_id),
    FOREIGN KEY (destination_site_id) REFERENCES sites (site_id)
);

CREATE TABLE IF NOT EXISTS path_segments (
    path_id        INTEGER NOT NULL,
    cell_index     BIGINT  NOT NULL,
    sequence_order INTEGER NOT NULL,
    path_quality   REAL    DEFAULT 0.1,
    PRIMARY KEY (path_id, cell_index),
    FOREIGN KEY (path_id)    REFERENCES paths (path_id),
    FOREIGN KEY (cell_index) REFERENCES cells (cell_index)
);

CREATE TABLE IF NOT EXISTS sphere_geometry (
    cell_index BIGINT PRIMARY KEY,
    pos_x      REAL,
    pos_y      REAL,
    pos_z      REAL,
    normal_x   REAL,
    normal_y   REAL,
    normal_z   REAL,
    FOREIGN KEY (cell_index) REFERENCES cells (cell_index)
);

CREATE TABLE IF NOT EXISTS ring_geometry (
    cell_index       BIGINT PRIMARY KEY,
    radius_distance  REAL,
    angular_theta    REAL,
    lateral_z        REAL,
    FOREIGN KEY (cell_index) REFERENCES cells (cell_index)
);
"""


def init_schema(con: sqlite3.Connection) -> None:
    """Create all world engine tables if they do not already exist.

    Args:
        con: An open SQLite connection. Caller owns the connection lifecycle.
    """
    con.executescript(_DDL)
