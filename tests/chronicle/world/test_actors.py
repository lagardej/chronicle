"""Tests for the minimal actor registry."""

import pytest

from chronicle.world.actors import (
    MovementComponent,
    PathComponent,
    PositionComponent,
    make_actor,
)


@pytest.mark.unit()
def test_make_actor_has_all_components() -> None:
    actor = make_actor(actor_id=1, cell_index=42, speed_kmh=5.0)

    assert set(actor.keys()) == {"position", "movement", "path"}


@pytest.mark.unit()
def test_make_actor_position() -> None:
    actor = make_actor(actor_id=1, cell_index=42, speed_kmh=5.0)

    assert actor["position"] == PositionComponent(cell_index=42)


@pytest.mark.unit()
def test_make_actor_movement() -> None:
    actor = make_actor(actor_id=1, cell_index=42, speed_kmh=5.0)

    assert actor["movement"] == MovementComponent(speed_kmh=5.0, terrain_modifier=1.0)


@pytest.mark.unit()
def test_make_actor_path_empty() -> None:
    actor = make_actor(actor_id=1, cell_index=42, speed_kmh=5.0)

    assert actor["path"] == PathComponent(waypoints=[], current_waypoint=0)


@pytest.mark.unit()
def test_registry_stores_actor() -> None:
    registry: dict[int, dict] = {}
    registry[1] = make_actor(actor_id=1, cell_index=42, speed_kmh=5.0)

    assert 1 in registry


@pytest.mark.unit()
def test_registry_independent_paths() -> None:
    a = make_actor(actor_id=1, cell_index=1, speed_kmh=5.0)
    b = make_actor(actor_id=2, cell_index=2, speed_kmh=5.0)

    a["path"].waypoints.append(99)

    assert b["path"].waypoints == []
