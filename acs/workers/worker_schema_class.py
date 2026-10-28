import time
import logging
import threading
from typing import Optional, Callable
import paho.mqtt.client as mqtt
from django.conf import settings


class WorkerThread(threading.Thread):
    """Base class for all background worker threads with controlled execution loop."""

    def __init__(self, thread_name: str, worker_name: str, loop_sleep_s: float = 0.5):
        super().__init__(name=thread_name, daemon=True)
        self.thread_name = thread_name
        self.worker_name = worker_name
        self.loop_sleep_s = loop_sleep_s
        self._running = True
        self.logger = logging.getLogger(f"worker.{worker_name}.{thread_name}")

    def run(self):
        self.logger.info(f"Starting worker thread: {self.thread_name}")
        while self._running:
            try:
                self.task()
            except Exception as e:
                self.logger.exception(f"Unhandled error in {self.thread_name}: {e}")
            time.sleep(self.loop_sleep_s)
        self.logger.info(f"Worker thread {self.thread_name} stopped cleanly.")

    def task(self):
        """Override this method with the worker loop task."""
        raise NotImplementedError("Subclasses must implement task()")

    def stop(self):
        self._running = False


class MQTTInterfaceWorker(WorkerThread):
    """Base worker equipped with an active MQTT Client connection to EMQX."""

    def __init__(
        self,
        thread_name: str,
        worker_name: str,
        loop_sleep_s: float = 0.5,
        host: Optional[str] = None,
        port: Optional[int] = None,
        client_id: Optional[str] = None,
    ):
        super().__init__(thread_name, worker_name, loop_sleep_s)
        self.mqtt_host = host or getattr(settings, "MQTT_BROKER_HOST", "127.0.0.1")
        self.mqtt_port = port or getattr(settings, "MQTT_BROKER_PORT", 1883)
        self.client_id = client_id or f"{worker_name}_{thread_name}_{int(time.time())}"

        self.client = mqtt.Client(client_id=self.client_id, clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self._is_connected = False
        self._connect_mqtt()

    def _connect_mqtt(self):
        try:
            self.logger.info(f"Connecting to MQTT Broker at {self.mqtt_host}:{self.mqtt_port}...")
            self.client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            self.logger.warning(f"Could not connect to MQTT Broker ({e}). Will retry on loop.")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker successfully (rc={rc})")
            self._is_connected = True
            self.on_mqtt_ready()
        else:
            self.logger.error(f"MQTT connect failed with return code {rc}")
            self._is_connected = False

    def _on_disconnect(self, client, userdata, rc):
        self.logger.warning(f"Disconnected from MQTT broker (rc={rc})")
        self._is_connected = False

    def _on_message(self, client, userdata, msg):
        try:
            self.on_message_received(msg.topic, msg.payload.decode("utf-8", errors="ignore"))
        except Exception as e:
            self.logger.error(f"Error handling message on {msg.topic}: {e}")

    def on_mqtt_ready(self):
        """Hook for subscriptions upon successful connection."""
        pass

    def on_message_received(self, topic: str, payload_str: str):
        """Hook for incoming MQTT messages."""
        pass

    def publish(self, topic: str, payload_str: str, qos: int = 1, retain: bool = False) -> bool:
        try:
            info = self.client.publish(topic, payload_str, qos=qos, retain=retain)
            return info.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            self.logger.error(f"Failed to publish to {topic}: {e}")
            return False

    def stop(self):
        super().stop()
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass
