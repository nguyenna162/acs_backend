import threading
from typing import Dict, Set, Optional


class ZoneManager:
    """Manages zone occupancy, speed limits, and admission control across factory traffic zones."""

    def __init__(self):
        self._lock = threading.Lock()
        self._zone_occupants: Dict[str, Set[str]] = {}  # zone_id -> set of amr_serials

    def can_enter_zone(self, amr_serial: str, zone_id: str, max_occupancy: int = 1) -> bool:
        with self._lock:
            current = self._zone_occupants.get(zone_id, set())
            if amr_serial in current:
                return True
            return len(current) < max_occupancy

    def enter_zone(self, amr_serial: str, zone_id: str, max_occupancy: int = 1) -> bool:
        with self._lock:
            current = self._zone_occupants.setdefault(zone_id, set())
            if amr_serial in current:
                return True
            if len(current) >= max_occupancy:
                return False
            current.add(amr_serial)
            return True

    def leave_zone(self, amr_serial: str, zone_id: str):
        with self._lock:
            if zone_id in self._zone_occupants:
                self._zone_occupants[zone_id].discard(amr_serial)

    def leave_all_zones(self, amr_serial: str):
        with self._lock:
            for occupants in self._zone_occupants.values():
                occupants.discard(amr_serial)

    def get_zone_occupants(self, zone_id: str) -> Set[str]:
        with self._lock:
            return set(self._zone_occupants.get(zone_id, set()))


default_zone_manager = ZoneManager()
