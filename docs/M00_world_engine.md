# Technical Design Document: The World Engine

**System Core Module:** Integrated Geography, Topology, Routing, and Multi-Scale LOD

**Architecture Paradigm:** Dual-Database CQRS Simulation Engine with Minimal Actor Registry

**Spatial Standard:** Uber H3 Hierarchical Hexagonal Grid (Aperture 7, native 64-bit index)

**Status:** Architectural Specification Phase (Python Proof of Concept)

---

## 1. System Vision & Philosophy

The foundational tenet of this engine is that **the world is the protagonist**. Actors—including the player—are transient entities whose capabilities, movement speeds, and operational choices are strictly constrained by the physical environment.

To build an unscripted, emergent universe, geography is treated as a dynamic, mutating database of physical variables. A static world map is simply a special case of this system where simulation loops are frozen.

The engine decouples the physical geometry of the world space (whether rendered as a sphere, plane, disc, or ringworld) from its underlying calculations. The physical laws of climate, hydrology, and friction remain completely identical because the world shape is abstracted into an unstructured hierarchical hexagonal graph network.

---

## 2. Dual-Database Paradigm (CQRS)

To balance dense global physical simulations with high-frequency actor updates and graph operations, the engine implements a Command Query Responsibility Segregation (CQRS) split. Both engines run inside the same Python process. **DuckDB reads from SQLite; it never writes back to it.** All mutations to SQLite are issued directly from Python via the `sqlite3` connection.

```
                  +----------------------------------+
                  |      Minimal Actor Registry      |
                  |  (Python dicts, 3 components)    |
                  +---+------------------------+-----+
                      |                        |
     DuckDB reads     |                        | Python writes directly
     LOD 0 via        |                        | via sqlite3 connection
     sqlite_scan()    v                        v
          +-------------------+     +-------------------+
          |      DuckDB       |     |      SQLite       |
          |  (OLAP Engine)    |     |  (OLTP Engine)    |
          |  LOD 0 physics    |     |  LOD 2 live cache |
          |  (read-only view) |     |  + actor state    |
          +-------------------+     +-------------------+
                                             |
                                             v
                                     game_save.db
                                     (single file, COMMIT)
```

### 2.1 The Division of Labor

* **The Dense Matrix (OLAP / DuckDB):** Responsible for global, continuous mathematical simulations. Reads LOD 0 cell data from SQLite via `sqlite_scan()` into columnar memory, runs vectorized climate equations (thermal diffusion, precipitation, wind advection), and returns results to Python as DataFrames. It does **not** write to SQLite.
* **The Sparse Network (OLTP / SQLite):** Single source of truth for all persistent state. Owns both LOD 0 macro cells (permanent) and LOD 2 local cells (sparse, instantiated on demand). Also owns actor state and path networks.
* **The Save State System:** SQLite is the save file. `COMMIT` on the SQLite connection writes the full current state to `game_save.db`.

### 2.2 Write-Back Protocol

After DuckDB completes a physics pass, Python reads the resulting DataFrame and writes mutations back to SQLite explicitly:

```python
# DuckDB reads LOD 0 cells, runs physics, returns results
df = duck_con.execute("""
    SELECT cell_index,
           25.0 - (elevation * 0.0065) AS updated_temp
    FROM sqlite_scan('game_save.db', 'cells')
    WHERE lod_level = 0
""").fetchdf()

# Python writes results directly to SQLite — DuckDB does not touch SQLite
rows = list(zip(df['updated_temp'], df['cell_index']))
sqlite_con.executemany(
    "UPDATE cells SET current_temperature = ? WHERE cell_index = ?", rows
)
sqlite_con.commit()
```

This keeps the DuckDB↔SQLite boundary clean: DuckDB is a read-only compute layer over SQLite data.

---

## 3. The Structural Cell & LOD Definition (Spatial Layer)

To remove spatial distortion and directional bias, the engine rejects traditional square grids. Square coordinates introduce mathematical discrepancies where diagonal steps are further than orthogonal steps ($\sqrt{2}$ vs $1$).

Instead, the core structure uses the **[Uber H3 library](https://h3geo.org/)** directly. H3 provides an Aperture 7 hierarchical hexagonal grid: each parent hexagon contains exactly 7 child hexagons at the next finer resolution — 1 center child surrounded by 6 children, one per edge. This gives the ~7x cell count increase per LOD step (86k → 4.2M → 100M+). H3 encodes every cell as a native 64-bit integer and provides O(1) parent/child/neighbor lookups without custom bitmask logic.

### 3.1 Level of Detail (LOD) Tiers

H3 supports 16 resolutions (0–15). The full range:

| H3 Res | Avg cell area   | Approx radius |
|--------|-----------------|---------------|
| 0      | ~4,250,000 km²  | ~1,300 km     |
| 1      | ~607,000 km²    | ~500 km       |
| 2      | ~86,700 km²     | ~86 km        |
| 3      | ~12,400 km²     | ~33 km        |
| 4      | ~1,770 km²      | ~22 km        |
| 5      | ~253 km²        | ~8 km         |
| 6      | ~36 km²         | ~4 km         |
| 7      | ~5.2 km²        | ~1.5 km       |
| 8      | ~0.74 km²       | ~460 m        |
| 9      | ~0.11 km²       | ~175 m        |
| 10     | ~0.015 km²      | ~65 m         |
| 11     | ~0.002 km²      | ~25 m         |
| 12     | ~0.0003 km²     | ~10 m         |
| 13     | ~45,000 m²      | ~4 m          |
| 14     | ~6,400 m²       | ~1.5 m        |
| 15     | ~900 m²         | ~0.5 m        |

The engine's LOD tiers map to specific H3 resolutions (TBD during POC):

| LOD | H3 Resolution | Cell radius | Cell count (Earth-sized) | Purpose                                                          |
|-----|---------------|-------------|--------------------------|------------------------------------------------------------------|
| 0   | H3 res 2      | ~86 km      | ~86,000                  | Macro climate, jet streams, tectonic loops                       |
| 1   | H3 res 4      | ~22 km      | ~4.2 million             | Regional biomes, faction territory (not instantiated during POC) |
| 2   | H3 res 6      | ~4 km       | ~100 million theoretical | Actor pathfinding, local weather — **sparse, on-demand only**    |

### 3.2 H3 as the Spatial Index

H3 cell indices are used directly as `cell_index` (BIGINT) primary keys throughout the schema. There is no custom bitmask layout. The H3 library provides:

* `h3.cell_to_parent(index, res)` — O(1) parent lookup (LOD 2 → LOD 0)
* `h3.grid_disk(index, k)` — k-ring neighbor traversal
* `h3.cell_to_latlng(index)` — coordinate projection for rendering

This eliminates the need to implement or maintain a custom 64-bit bitmask encoding.

---

## 4. Asymmetrical Data Simulation Strategy

LOD 0 cells are **permanent** in SQLite (only ~86,000 rows). LOD 2 cells and their adjacency edges are **sparse and transient** — instantiated when an actor enters a region, purged when all actors leave and the cell is unmodified.

```
+-----------------------------------------------------------+
|                      DUCKDB (compute)                     |
|  Reads LOD 0 rows via sqlite_scan()                       |
|  Runs vectorized climate equations                        |
|  Returns DataFrames to Python                             |
+-----------------------------+-----------------------------+
                              |
                              v  Python writes back via sqlite3
+-----------------------------v-----------------------------+
|                      SQLITE (state)                       |
|  LOD 0 cells — permanent, ~86k rows                       |
|  LOD 2 cells — sparse, instantiated per active region     |
|  LOD 2 adjacency — sparse, co-instantiated with cells     |
|  Actor state — always present while actors exist          |
+-----------------------------------------------------------+
```

* **Global Macro Ticks (Dense & Permanent):** DuckDB processes all LOD 0 rows on each macro tick. Python writes results back to SQLite.
* **Local Micro Ticks (Sparse & Transient):** LOD 2 cells are instantiated in SQLite when an actor's `PositionComponent` registers presence. Their 6 adjacency edges are instantiated at the same time. On region vacate, unmodified rows are purged.
* **Topographical Downsampling:** On LOD 2 instantiation, the engine reads the parent LOD 0 cell from SQLite and interpolates its values (temperature, precipitation, elevation gradient) to seed the new LOD 2 rows.

---

## 5. Unified Database Schema

All tables live in SQLite (`game_save.db`). DuckDB accesses them read-only via `sqlite_scan()`.

The schema enforces LOD ownership via the `lod_level` column: LOD 0 rows are permanent; LOD 2 rows are transient. No shared ambiguity.

### 5.1 Core Simulation Tables (Topological)

```sql
-- Core State Ledger
-- LOD 0 rows: permanent. LOD 2 rows: sparse, instantiated on demand.
CREATE TABLE cells (
    cell_index BIGINT PRIMARY KEY,           -- Native H3 64-bit index (no custom encoding)
    lod_level INTEGER NOT NULL,              -- 0 = Macro (permanent), 2 = Local (transient)
    elevation REAL NOT NULL DEFAULT 0.0,     -- Metres relative to baseline
    crust_thickness REAL NOT NULL DEFAULT 30.0, -- For tectonic/volcanic simulations
    water_table REAL NOT NULL DEFAULT 0.0,   -- Internal H2O volume
    precipitation REAL NOT NULL DEFAULT 0.0, -- Accumulated moisture
    current_temperature REAL DEFAULT 20.0,   -- Ambient thermal state
    biomass REAL NOT NULL DEFAULT 1.0,       -- Vegetation/organic matter
    soil_fertility REAL NOT NULL DEFAULT 0.0,
    current_mud_factor REAL DEFAULT 0.0      -- Dynamic traversal modifier
);

-- Topology Graph Network
-- LOD 0 adjacency: permanent (~516k rows). LOD 2 adjacency: sparse, co-instantiated with cells.
-- Only rows whose origin_index exists in the cells table are kept.
CREATE TABLE adjacency (
    origin_index BIGINT NOT NULL,
    neighbor_index BIGINT NOT NULL,
    lod_level INTEGER NOT NULL,              -- Mirrors parent cell lod_level for fast filtering
    distance REAL NOT NULL,                  -- Centroid-to-centroid distance (km)
    flux_coefficient REAL DEFAULT 1.0,       -- Thermal/hydrological conductivity
    PRIMARY KEY (origin_index, neighbor_index),
    FOREIGN KEY (origin_index) REFERENCES cells(cell_index)
);

-- Fixed Geographic Anchors (Settlements, Hubs, Interest Points)
CREATE TABLE sites (
    site_id INTEGER PRIMARY KEY,
    cell_index BIGINT NOT NULL,
    site_type TEXT NOT NULL,                 -- 'village', 'ruin', 'battlefield', etc.
    name TEXT NOT NULL,
    FOREIGN KEY (cell_index) REFERENCES cells(cell_index)
);

-- Master Infrastructure Networks
CREATE TABLE paths (
    path_id INTEGER PRIMARY KEY,
    origin_site_id INTEGER,
    destination_site_id INTEGER,
    name TEXT,
    FOREIGN KEY (origin_site_id) REFERENCES sites(site_id),
    FOREIGN KEY (destination_site_id) REFERENCES sites(site_id)
);

-- Infrastructure Chain Overlays
CREATE TABLE path_segments (
    path_id INTEGER,
    cell_index BIGINT,
    sequence_order INTEGER,
    path_quality REAL DEFAULT 0.1,           -- 0.0 (desire trail) to 1.0 (paved highway)
    PRIMARY KEY (path_id, cell_index),
    FOREIGN KEY (path_id) REFERENCES paths(path_id),
    FOREIGN KEY (cell_index) REFERENCES cells(cell_index)
);
```

### 5.2 Geometric Projection Tables (Shape Layouts)

Hidden from physics. Used only by the presentation layer to translate `cell_index` into visual coordinates.

```sql
-- Option A: Planetary Spherical Projection
CREATE TABLE sphere_geometry (
    cell_index BIGINT PRIMARY KEY,
    pos_x REAL, pos_y REAL, pos_z REAL,
    normal_x REAL, normal_y REAL, normal_z REAL,
    FOREIGN KEY (cell_index) REFERENCES cells(cell_index)
);

-- Option B: Orbital Ringworld Projection
CREATE TABLE ring_geometry (
    cell_index BIGINT PRIMARY KEY,
    radius_distance REAL,
    angular_theta REAL,
    lateral_z REAL,
    FOREIGN KEY (cell_index) REFERENCES cells(cell_index)
);
```

---

## 6. Simulation & Path Routing Execution

### 6.1 Hierarchical Routing Pass

Long-distance routing avoids per-cell explosion by traversing up to LOD 0 and back down:

```
[Actor at LOD 2 cell] -> [h3.cell_to_parent() to LOD 0] -> [A* across LOD 0 macro graph]
    -> [h3.cell_to_children() at destination LOD 0] -> [A* final approach at LOD 2]
```

1. Actor calculates a short LOD 2 path to the edge of their current macro cell.
2. Routing upsamples to LOD 0, resolving the long-distance leg across macro edges only.
3. On approach, routing downsamples to LOD 2 for final placement at the destination site.

H3's native parent/child functions handle steps 1↔2 and 2↔3 without custom index math.

### 6.2 Set-Based Physics & Cost Verification

DuckDB executes physics vectorially, reading from SQLite. Python writes results back:

```sql
-- Thermal lapse rate (run inside DuckDB, against sqlite_scan result)
SELECT cell_index, 25.0 - (elevation * 0.0065) AS updated_temp
FROM sqlite_scan('game_save.db', 'cells')
WHERE lod_level = 0;

-- Thermodynamic diffusion across adjacency edges
WITH neighbor_averages AS (
    SELECT a.origin_index, AVG(c.current_temperature) AS avg_temp
    FROM sqlite_scan('game_save.db', 'adjacency') a
    JOIN sqlite_scan('game_save.db', 'cells') c ON a.neighbor_index = c.cell_index
    WHERE a.lod_level = 0
    GROUP BY a.origin_index
)
SELECT origin_index,
       (current_temperature + (avg_temp - current_temperature) * 0.1) AS new_temp
FROM neighbor_averages
JOIN sqlite_scan('game_save.db', 'cells') ON cell_index = origin_index;
```

Traversal cost weight for actor movement:

$$W = \frac{\text{Distance} \times \text{Terrain Friction}}{\text{Path Quality} \times \text{Weather Modifier} \times \text{Actor Capability}}$$

---

## 7. Minimal Actor Registry (Geography POC)

A full ECS is not warranted for geography and movement work. During the POC phase, actors are plain Python dataclasses stored in a dict keyed by actor ID.

**Three components only:**

```python
from dataclasses import dataclass, field

@dataclass
class PositionComponent:
    cell_index: int          # Current H3 cell index (LOD 2)

@dataclass
class MovementComponent:
    speed_kmh: float         # Base movement speed
    terrain_modifier: float  # Multiplier applied per cell type (road, mud, etc.)

@dataclass
class PathComponent:
    waypoints: list[int] = field(default_factory=list)  # Ordered H3 cell indices
    current_waypoint: int = 0

# Registry: actor_id -> dict of components
ActorRegistry = dict[int, dict]

def make_actor(actor_id: int, cell_index: int, speed_kmh: float) -> dict:
    return {
        "position": PositionComponent(cell_index=cell_index),
        "movement": MovementComponent(speed_kmh=speed_kmh, terrain_modifier=1.0),
        "path": PathComponent(),
    }
```

`PositionComponent` is the trigger for LOD 2 cell instantiation: when an actor's `cell_index` is set, the engine checks whether that LOD 2 cell (and its 6 adjacency edges) exist in SQLite, creating them if not.

A full ECS (component iteration, system scheduling, archetype storage) is deferred until actor counts and behavioral complexity justify it.

---

## 8. Python Implementation Protocol

```python
import sqlite3
import duckdb

def initialize_engine(save_path: str = "game_save.db"):
    # SQLite: source of truth, handles all writes
    sqlite_con = sqlite3.connect(save_path)
    sqlite_con.execute("PRAGMA journal_mode=WAL;")

    # DuckDB: in-memory compute layer, reads SQLite read-only
    duck_con = duckdb.connect(":memory:")
    duck_con.execute("INSTALL sqlite; LOAD sqlite;")
    # DuckDB reads via sqlite_scan() — no ATTACH, no write-back through DuckDB

    return sqlite_con, duck_con


def run_simulation_frame(
    sqlite_con: sqlite3.Connection,
    duck_con: duckdb.DuckDBPyConnection,
    actor_registry: dict,
    current_tick: int,
    save_path: str = "game_save.db",
):
    # Step A: Actor movement (high-frequency, every tick)
    run_actor_movement(actor_registry, sqlite_con, save_path)

    # Step B: Global physics (low-frequency, every 100 ticks)
    if current_tick % 100 == 0:
        df = duck_con.execute(f"""
            SELECT cell_index,
                   25.0 - (elevation * 0.0065) AS updated_temp,
                   CASE WHEN water_table > 0.75 THEN 1.0 ELSE 0.0 END AS mud
            FROM sqlite_scan('{save_path}', 'cells')
            WHERE lod_level = 0
        """).fetchdf()

        # Write results back to SQLite directly — not through DuckDB
        rows = list(zip(df["updated_temp"], df["mud"], df["cell_index"]))
        sqlite_con.executemany(
            "UPDATE cells SET current_temperature = ?, current_mud_factor = ? "
            "WHERE cell_index = ?",
            rows,
        )
        sqlite_con.commit()
```

---

## 9. Scope Boundary: History Generator

This document covers the world engine (geography, physics, actor movement). The history generator — which produces the pre-play record of wars, dynasties, disasters, and technological state that the world engine reads at game start — is a separate module, specified elsewhere.

The world engine assumes a populated `cells`, `sites`, and `paths` schema as input. Producing that initial state is the history generator's responsibility.
