from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class OperatingMode(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    SEMIAUTOMATIC = "SEMIAUTOMATIC"
    MANUAL = "MANUAL"
    SERVICE = "SERVICE"
    TEACHIN = "TEACHIN"


class EStop(str, Enum):
    AUTOACK = "autoAck"
    MANUAL = "manual"
    REMOTE = "remote"
    NONE = "none"


@dataclass
class BatteryState:
    batteryCharge: float
    batteryHealth: Optional[float] = None
    charging: bool = False
    batteryVoltage: Optional[float] = None
    reach: Optional[float] = None


@dataclass
class SafetyState:
    eStop: str = EStop.NONE.value
    fieldViolation: bool = False


@dataclass
class AGVPosition:
    x: float
    y: float
    theta: float
    mapId: str
    positionInitialized: bool = True
    localizationScore: Optional[float] = 1.0


@dataclass
class Velocity:
    vx: float = 0.0
    vy: float = 0.0
    omega: float = 0.0


@dataclass
class OrderState:
    headerId: int
    timestamp: str
    version: str
    manufacturer: str
    serialNumber: str
    orderId: str
    orderUpdateId: int
    lastNodeId: str
    lastNodeSequenceId: int
    driving: bool
    operatingMode: str = OperatingMode.AUTOMATIC.value
    nodeStates: List[Dict[str, Any]] = field(default_factory=list)
    edgeStates: List[Dict[str, Any]] = field(default_factory=list)
    actionStates: List[Dict[str, Any]] = field(default_factory=list)
    batteryState: Optional[Dict[str, Any]] = None
    safetyState: Optional[Dict[str, Any]] = None
    agvPosition: Optional[Dict[str, Any]] = None
    velocity: Optional[Dict[str, Any]] = None
    loads: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    information: List[Dict[str, Any]] = field(default_factory=list)
    paused: bool = False
    newBaseRequest: bool = False
    distanceSinceLastNode: Optional[float] = 0.0
