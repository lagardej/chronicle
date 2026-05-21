"""Minimal actor registry for the geography POC.

A full ECS is deferred until actor counts and behavioural complexity justify it.
For now, actors are plain dataclasses stored in a dict keyed by actor ID.
"""

from dataclasses import dataclass, field

__all__ = [
    "ActorRegistry",
    "MovementComponent",
    "PathComponent",
    "PositionComponent",
    "make_actor",
]

ActorRegistry = dict[int, dict]


@dataclass
class PositionComponent:
    """Current location of an actor as an H3 cell index (LOD 2)."""

    cell_index: str


@dataclass
class MovementComponent:
    """Movement capabilities of an actor."""

    speed_kmh: float
    terrain_modifier: float = 1.0


@dataclass
class PathComponent:
    """Queued waypoints for an actor's current journey."""

    waypoints: list[str] = field(default_factory=list)
    current_waypoint: int = 0


def make_actor(actor_id: int, cell_index: str, speed_kmh: float) -> dict:
    """Create a new actor entry for the registry.

    Args:
        actor_id: Unique identifier for the actor.
        cell_index: Starting H3 cell index (LOD 2).
        speed_kmh: Base movement speed in km/h.

    Returns:
        A dict of components keyed by component name.
    """
    return {
        "position": PositionComponent(cell_index=cell_index),
        "movement": MovementComponent(speed_kmh=speed_kmh),
        "path": PathComponent(),
    }
