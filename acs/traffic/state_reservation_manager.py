import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .models import ReservationStatus, RobotPriority


@dataclass
class TimeReservation:
    robot_id: str
    resource_type: str  # "node" or "edge"
    resource_id: str
    start_time: float
    end_time: float
    priority: int = RobotPriority.NORMAL


class StateReservationManager:
    """Manages spatio-temporal reservations for factory floor resources (nodes & edges) to prevent collisions and deadlocks."""

    def __init__(self):
        self._lock = threading.RLock()
        self._reservations: Dict[str, List[TimeReservation]] = {}  # "type:id" -> list of TimeReservation

    def _key(self, resource_type: str, resource_id: str) -> str:
        return f"{resource_type}:{resource_id}"

    def can_reserve(self, robot_id: str, resource_type: str, resource_id: str, start_time: float, end_time: float, priority: int = RobotPriority.NORMAL) -> bool:
        key = self._key(resource_type, resource_id)
        with self._lock:
            existing_list = self._reservations.get(key, [])
            now = time.time()
            # Clean expired reservations
            active_list = [r for r in existing_list if r.end_time > now]
            self._reservations[key] = active_list

            for res in active_list:
                if res.robot_id == robot_id:
                    continue  # Same robot can extend or overlap its own reservation
                # Check time overlap
                if not (end_time <= res.start_time or start_time >= res.end_time):
                    # Overlap detected
                    if priority <= res.priority:
                        return False
            return True

    def reserve(self, robot_id: str, resource_type: str, resource_id: str, start_time: float, end_time: float, priority: int = RobotPriority.NORMAL) -> bool:
        key = self._key(resource_type, resource_id)
        with self._lock:
            if not self.can_reserve(robot_id, resource_type, resource_id, start_time, end_time, priority):
                return False

            reservation = TimeReservation(
                robot_id=robot_id,
                resource_type=resource_type,
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
                priority=priority,
            )
            self._reservations.setdefault(key, []).append(reservation)
            return True

    def release(self, robot_id: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        with self._lock:
            if resource_type and resource_id:
                key = self._key(resource_type, resource_id)
                if key in self._reservations:
                    self._reservations[key] = [r for r in self._reservations[key] if r.robot_id != robot_id]
            else:
                for key in list(self._reservations.keys()):
                    self._reservations[key] = [r for r in self._reservations[key] if r.robot_id != robot_id]

    def get_status(self, resource_type: str, resource_id: str) -> ReservationStatus:
        key = self._key(resource_type, resource_id)
        now = time.time()
        with self._lock:
            active = [r for r in self._reservations.get(key, []) if r.end_time > now]
            if not active:
                return ReservationStatus.FREE
            # If current time is inside a reservation window
            for r in active:
                if r.start_time <= now <= r.end_time:
                    return ReservationStatus.OCCUPIED
            return ReservationStatus.RESERVED


# Singleton instance
default_reservation_manager = StateReservationManager()
