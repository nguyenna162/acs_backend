from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class BlockingType(str, Enum):
    NONE = "NONE"
    SOFT = "SOFT"
    HARD = "HARD"


class ActionStatus(str, Enum):
    WAITING = "WAITING"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


@dataclass
class ActionParameter:
    key: str
    value: Any


@dataclass
class Action:
    actionId: str
    actionType: str
    blockingType: str = BlockingType.NONE.value
    actionDescription: Optional[str] = None
    actionParameters: Optional[List[Dict[str, Any]]] = field(default_factory=list)


@dataclass
class ActionState:
    actionId: str
    actionType: str
    actionStatus: str = ActionStatus.WAITING.value
    actionDescription: Optional[str] = None
    resultDescription: Optional[str] = None
