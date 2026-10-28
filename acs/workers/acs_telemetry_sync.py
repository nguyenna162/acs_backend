import os
import sys
import time
import json
import logging
from datetime import datetime, timezone, timedelta
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "acs.settings")
    django.setup()

from amr.models import AmrVehicle, AmrStateLog
from workers.worker_schema_class import MQTTInterfaceWorker

logger = logging.getLogger("workers.acs_telemetry_sync")


class TelemetrySyncWorker(MQTTInterfaceWorker):
    """Subscribes to VDA 5050 state topics and synchronizes telemetry into AmrVehicle and AmrStateLog."""

    def __init__(
        self,
        thread_name="telemetry_sync_worker",
        worker_name="acs_telemetry_sync",
        loop_sleep_s=0.5,
    ):
        super().__init__(thread_name, worker_name, loop_sleep_s)

    def on_mqtt_ready(self):
        # Subscribe to standard VDA 5050 state topic pattern: uagv/v2/+/+/state
        topic_pattern = "uagv/v2/+/+/state"
        self.logger.info(f"Subscribing to telemetry topic pattern: {topic_pattern}")
        self.client.subscribe(topic_pattern, qos=1)

        # Also subscribe to connection topic pattern: uagv/v2/+/+/connection
        conn_pattern = "uagv/v2/+/+/connection"
        self.client.subscribe(conn_pattern, qos=1)

    def on_message_received(self, topic: str, payload_str: str):
        try:
            data = json.loads(payload_str)
        except Exception as e:
            self.logger.warning(f"Invalid JSON payload on {topic}: {e}")
            return

        parts = topic.split("/")
        # Expected: uagv / v2 / {manufacturer} / {serialNumber} / {topic_type}
        if len(parts) >= 5:
            manufacturer = parts[2]
            serial_number = parts[3]
            topic_type = parts[4]
        else:
            serial_number = data.get("serialNumber")
            topic_type = "state"

        if not serial_number:
            return

        if topic_type == "connection":
            conn_state = data.get("connectionState", "ONLINE")
            is_online = conn_state == "ONLINE"
            AmrVehicle.objects.filter(serial_number=serial_number).update(
                is_online=is_online,
                last_heartbeat=datetime.now(timezone.utc),
            )
            return

        # Handle VDA 5050 State Message
        order_id = str(data.get("orderId", ""))
        order_update_id = int(data.get("orderUpdateId", 0))
        last_node_id = str(data.get("lastNodeId", ""))
        driving = bool(data.get("driving", False))
        paused = bool(data.get("paused", False))
        new_base_request = bool(data.get("newBaseRequest", False))
        operating_mode = str(data.get("operatingMode", "AUTOMATIC"))

        agv_pos = data.get("agvPosition", {})
        velocity = data.get("velocity", {})
        battery = data.get("batteryState", {})
        safety = data.get("safetyState", {})
        node_states = data.get("nodeStates", [])
        edge_states = data.get("edgeStates", [])
        action_states = data.get("actionStates", [])
        loads = data.get("loads", [])
        errors = data.get("errors", [])
        information = data.get("information", [])

        # Update or create AmrVehicle
        amr, created = AmrVehicle.objects.get_or_create(
            serial_number=serial_number,
            defaults={
                "manufacturer": data.get("manufacturer", "SEVT"),
                "version": data.get("version", "2.1.0"),
                "is_online": True,
                "is_idle": not driving and not order_id,
            },
        )

        amr.is_online = True
        amr.last_heartbeat = datetime.now(timezone.utc)
        amr.order_id = order_id
        amr.order_update_id = order_update_id
        amr.last_node_id = last_node_id
        amr.driving = driving
        amr.paused = paused
        amr.new_base_request = new_base_request
        amr.operating_mode = operating_mode
        amr.amr_position = agv_pos
        amr.velocity = velocity
        amr.battery_state = battery
        amr.safety_state = safety
        amr.node_states = node_states
        amr.edge_states = edge_states
        amr.action_state = action_states
        amr.loads = loads
        amr.errors = errors
        amr.information = information
        amr.is_idle = not driving and not order_id and not loads
        amr.save()

        # Audit log into AmrStateLog
        AmrStateLog.objects.create(
            serialNumber=amr,
            order_id=order_id,
            order_update_id=order_update_id,
            operating_mode=operating_mode,
            node_state=node_states,
            edge_state=edge_states,
            action_state=action_states,
            loads=loads,
            errors=errors,
            information=information,
            amr_position=agv_pos,
            velocity=velocity,
            battery_state=battery,
            safety_state=safety,
            driving=driving,
            paused=paused,
            new_base_request=new_base_request,
        )

    def task(self):
        # Heartbeat check for AMR online status (timeout 30s)
        timeout_threshold = datetime.now(timezone.utc) - timedelta(seconds=30)
        AmrVehicle.objects.filter(is_online=True, last_heartbeat__lt=timeout_threshold).update(is_online=False)


def main():
    worker = TelemetrySyncWorker()
    worker.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()
        worker.join(timeout=3)


if __name__ == "__main__":
    main()
