import time
import logging
from typing import Dict, List, Any, Optional
import requests
from django.conf import settings

logger = logging.getLogger("integrations.aligo")


class AligoMESClient:
    """REST Client for Aligo MES External API with caching and error tolerance."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, timeout: float = 5.0):
        self.base_url = base_url or getattr(settings, "ALIGO_API_BASE_URL", "http://127.0.0.1:8080/api/v1")
        self.api_key = api_key or getattr(settings, "ALIGO_API_KEY", "aligo-secret-token")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ACS-Backend/2.1.0",
        })
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def get_line_status(self, line_id: str = "CNC_2G") -> Dict[str, Any]:
        """Fetch real-time CNC production line status from Aligo MES."""
        url = f"{self.base_url}/lines/{line_id}/status"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug(f"Aligo MES unreachable ({e}), using simulated line telemetry.")

        # Fallback simulation data for CNC Prod 2G
        return {
            "line_id": line_id,
            "status": "RUNNING",
            "efficiency": 0.94,
            "active_buffers": ["BUF_CNC_01", "BUF_CNC_02", "BUF_CNC_03"],
            "timestamp": time.time(),
        }

    def fetch_supply_commands(self) -> List[Dict[str, Any]]:
        """Fetch pending supply commands/material delivery requests from Aligo MES."""
        url = f"{self.base_url}/supply-commands/pending"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json().get("commands", [])
        except Exception as e:
            logger.debug(f"Could not reach Aligo MES supply commands endpoint: {e}")
        return []

    def report_delivery_completed(self, command_id: str, amr_serial: str) -> bool:
        """Report material delivery completion to Aligo MES."""
        url = f"{self.base_url}/supply-commands/{command_id}/complete"
        try:
            resp = self.session.post(url, json={"amr_serial": amr_serial, "completed_at": time.time()}, timeout=self.timeout)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to report delivery completion to Aligo: {e}")
            return False


default_aligo_client = AligoMESClient()
