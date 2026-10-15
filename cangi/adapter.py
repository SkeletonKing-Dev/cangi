from abc import ABC, abstractmethod
from typing import Callable, List, Tuple

from .schema import Action, Constraint, DocumentState, Entity, SolverState


class PlatformAdapter(ABC):
    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def get_document_state(self) -> DocumentState: ...

    @abstractmethod
    def get_entity(self, entity_id: str) -> Entity: ...

    @abstractmethod
    def get_constraints(self) -> List[Constraint]: ...

    @abstractmethod
    def get_solver_state(self) -> SolverState: ...

    @abstractmethod
    def subscribe(self, callback: Callable[[Action], None]) -> None: ...

    @abstractmethod
    def world_to_screen(self, x: float, y: float, z: float = 0.0) -> Tuple[float, float]:
        """Model coordinates to global screen pixels."""
