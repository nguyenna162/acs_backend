import threading
from datetime import datetime, timezone


def get_vda5050_topic(interface: str, manufacturer: str, serial_number: str, topic_type: str) -> str:
    """Format standard VDA 5050 MQTT topic:
    interface/v2/manufacturer/serialNumber/topic_type
    e.g., uagv/v2/SEVT/AMR_001/order
    """
    prefix = interface if interface else "uagv"
    return f"{prefix}/v2/{manufacturer}/{serial_number}/{topic_type}"


class MsgHeader:
    """Helper managing VDA 5050 message headers and sequence IDs."""

    def __init__(self, topic_control=None, manufacturer: str = "SEVT", version: str = "2.1.0", serial_number: str = ""):
        self.lock = threading.Lock()
        self.topic_control = topic_control
        self.manufacturer = manufacturer
        self.version = version
        self.serial_number = serial_number
        if topic_control:
            self.manufacturer = getattr(topic_control, "manufacturer", manufacturer)
            self.version = getattr(topic_control, "version", version)
            self.topic = getattr(topic_control, "topic", "")
            self._header_id = getattr(topic_control, "header_id", 0)
        else:
            self.topic = get_vda5050_topic("uagv", manufacturer, serial_number, "order")
            self._header_id = 0

    def get_current_header_id_and_increase(self) -> int:
        with self.lock:
            self._header_id += 1
            if self.topic_control:
                self.topic_control.header_id = self._header_id
                self.topic_control.save(update_fields=["header_id", "last_call"])
            return self._header_id

    @staticmethod
    def get_current_timestamp_utc() -> str:
        return datetime.now(timezone.utc).isoformat()
