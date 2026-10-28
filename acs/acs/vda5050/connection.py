from dataclasses import dataclass
from enum import Enum


class ConnectionStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    CONNECTIONBROKEN = "CONNECTIONBROKEN"


@dataclass
class ConnectionState:
    headerId: int
    timestamp: str
    version: str
    manufacturer: str
    serialNumber: str
    connectionState: str = ConnectionStatus.ONLINE.value
