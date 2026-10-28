from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .action import Action


@dataclass
class NodePosition:
    x: float
    y: float
    theta: Optional[float] = 0.0
    mapId: Optional[str] = ""
    allowedDeviationXy: Optional[float] = 0.05
    allowedDeviationTheta: Optional[float] = 0.05


@dataclass
class Node:
    nodeId: str
    sequenceId: int
    released: bool
    actions: List[Dict[str, Any]] = field(default_factory=list)
    nodePosition: Optional[Dict[str, Any]] = None
    nodeDescription: Optional[str] = None


@dataclass
class Edge:
    edgeId: str
    sequenceId: int
    released: bool
    startNodeId: str
    endNodeId: str
    actions: List[Dict[str, Any]] = field(default_factory=list)
    edgeDescription: Optional[str] = None
    maxSpeed: Optional[float] = None
    maxRotationSpeed: Optional[float] = None
    orientation: Optional[float] = None
    orientationType: Optional[str] = "TANGENTIAL"
    direction: Optional[str] = "FORWARD"
    rotationAllowed: Optional[bool] = True
    length: Optional[float] = None
    trajectory: Optional[Dict[str, Any]] = None


@dataclass
class Order:
    headerId: int
    timestamp: str
    version: str
    manufacturer: str
    serialNumber: str
    orderId: str
    orderUpdateId: int
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    zoneSetId: Optional[str] = None
