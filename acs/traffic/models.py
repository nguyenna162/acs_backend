from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone


class RobotPriority(IntEnum):
    URGENT = 10
    HIGH = 7
    NORMAL = 5
    LOW = 1


class ReservationStatus(str, Enum):
    FREE = "FREE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    BLOCKED = "BLOCKED"


@dataclass
class FleetTask:
    task_id: str
    order_id: str
    source_node_id: str
    target_node_id: str
    priority: int = RobotPriority.NORMAL
    sla_deadline: Optional[datetime] = None
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FleetAssignment:
    robot_serial: str
    task_id: str
    order_id: str
    cost: float
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FleetSchedulerResult:
    assignments: List[FleetAssignment] = field(default_factory=list)
    unassigned_robots: List[str] = field(default_factory=list)
    unassigned_tasks: List[str] = field(default_factory=list)
    total_cost: float = 0.0
    algorithm_used: str = "HUNGARIAN"
