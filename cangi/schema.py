import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

PLATFORMS = ("freecad", "autocad", "qcad")

EVENT_TYPES = (
    "document_created", "document_activated", "document_closed",
    "object_created", "object_modified", "object_deleted",
    "command_start", "command_end", "selection_changed",
)


@dataclass(frozen=True)
class Event:
    timestamp_ns: int
    platform: str
    event_type: str
    entity_id: str = ""
    entity_type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    command_context: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


Action = Event


@dataclass
class Entity:
    id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Constraint:
    id: str
    type: str
    entity_ids: List[str] = field(default_factory=list)
    value: Optional[float] = None


@dataclass
class SolverState:
    fully_constrained: Optional[bool] = None
    dof: Optional[int] = None
    messages: List[str] = field(default_factory=list)


@dataclass
class DocumentState:
    name: str
    entities: List[Entity] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    solver: SolverState = field(default_factory=SolverState)
