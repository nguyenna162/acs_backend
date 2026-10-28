import os
import sys
import queue
import signal
import threading
import time
import json
import logging
from dataclasses import asdict

import django
from django.db import transaction
from django.utils import timezone

# Setup Django if standalone
if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "acs.settings")
    django.setup()

import acs.vda5050.order as vda_5050_order
import acs.vda5050.action as vda_5050_action
from acs.vda5050.topic import MsgHeader
from amr.models import AmrVehicle, TopicControl
from acs.models import OrderMaster, Order, SubOrder, ActionDispatch
from map.models import Node, Edge
from workers.worker_schema_class import WorkerThread, MQTTInterfaceWorker

WORKER_NAME = os.path.basename(__file__).replace(".py", "")

# database, django model setup
try:
    worker_django_user, _ = django.contrib.auth.get_user_model().objects.get_or_create(
        username=WORKER_NAME,
        defaults={
            "email": "tran@tran.sam",
            "password": WORKER_NAME,
            "is_staff": False,
            "is_superuser": False,
        },
    )
except Exception:
    worker_django_user = None

#################################################################
# START WORKER DEFINITION
#################################################################

queue_order_2_sent = queue.Queue(maxsize=1000)

SENT_TIMEOUT_SECONDS = 300
RESEND_INTERVAL_SECONDS = 3.0

_anchor_lock = threading.Lock()
_sent_anchor_history = {}
_last_sent_anchor_seq = {}
MAX_RAM_CACHE_SIZE = 20000

_dispatched_lock = threading.Lock()
_dispatched_in_flight = set()

_pending_publishes = {}
_pending_lock = threading.Lock()


def _register_dispatched_actions(suborder, amr, order_msg_dict, logger):
    for node in order_msg_dict.get("nodes", []) or []:
        for act in node.get("actions", []) or []:
            action_id = act.get("actionId")
            if not action_id:
                continue
            # FIX 1.2/2.1: Wrap inside atomic block if needed elsewhere
            try:
                _, created = ActionDispatch.objects.get_or_create(
                    id=action_id,
                    defaults={
                        "sub_order": suborder,
                        "order": suborder.order,
                        "amr": amr,
                        "action_type": act.get("actionType", "UNKNOWN"),
                        "blocking_type": act.get("blockingType") or "NONE",
                    },
                )
            except Exception as e:
                log_fn = getattr(logger, "logger", logger)
                log_fn.warning(f"Failed to register action {action_id}: {e}")


def _resolve_anchor_seq(need_send_suborder, handle_amr, nodes):
    if not nodes:
        return None
    node_seq = nodes[0].get("sequenceId")
    amr_seq = getattr(handle_amr, "order_update_id", None)
    try:
        amr_seq = int(amr_seq) if amr_seq is not None else None
    except (TypeError, ValueError):
        amr_seq = None

    if amr_seq is not None and amr_seq > 0 and amr_seq != node_seq:
        return None

    accepted_ouid = getattr(handle_amr, "order_update_id", None)
    try:
        accepted_ouid = int(accepted_ouid) if accepted_ouid is not None else None
    except (TypeError, ValueError):
        accepted_ouid = None

    sub_id_str = str(need_send_suborder.id)
    ouid_str = str(accepted_ouid) if accepted_ouid is not None else None

    with _anchor_lock:
        if ouid_str is not None:
            anchor_seq = _sent_anchor_history.get(sub_id_str, {}).get(ouid_str)
            if anchor_seq is not None:
                return int(anchor_seq)
        anchor_seq = _last_sent_anchor_seq.get(sub_id_str)
        if anchor_seq is not None:
            return int(anchor_seq)
    return node_seq if node_seq is not None else 0


def _amr_ready_for_update(need_send_suborder, handle_amr) -> bool:
    nodes = (
        need_send_suborder.path.get("nodes", [])
        if isinstance(need_send_suborder.path, dict)
        else []
    )
    anchor_seq = _resolve_anchor_seq(need_send_suborder, handle_amr, nodes)
    if anchor_seq is None:
        return False
    return (
        getattr(handle_amr, "order_id", "") == str(need_send_suborder.order.id)
        and getattr(handle_amr, "new_base_request", None) is True
    )


class SubOrderDispatcher(WorkerThread):
    def __init__(
        self,
        thread_name="suborder_dispatcher",
        worker_name=WORKER_NAME,
        loop_sleep_s=0.5,
    ):
        super().__init__(thread_name, worker_name, loop_sleep_s)

    def task(self):
        active_order_masters = OrderMaster.objects.filter(
            status=OrderMaster.Status.PROCESSING
        )
        for order_master in active_order_masters.iterator(chunk_size=100):
            try:
                handle_amr = AmrVehicle.objects.get(is_used_by_master=order_master)
            except AmrVehicle.MultipleObjectsReturned:
                handle_amr_list = AmrVehicle.objects.filter(
                    is_used_by_master=order_master
                )
                handle_amr = handle_amr_list.first()
            except AmrVehicle.DoesNotExist:
                continue

            if not handle_amr:
                continue

            pending_suborders = SubOrder.objects.filter(
                order_master=order_master,
                status=SubOrder.Status.PENDING,
            ).order_by("order_update_id")

            need_send_suborder = pending_suborders.first()
            if not need_send_suborder:
                continue

            sub_id_str = str(need_send_suborder.id)
            with _dispatched_lock:
                if sub_id_str in _dispatched_in_flight:
                    continue

            # Check if this is initial base order or update order
            is_initial = need_send_suborder.order_update_id == 0 or getattr(handle_amr, "order_id", "") != str(need_send_suborder.order.id)
            if not is_initial and not _amr_ready_for_update(need_send_suborder, handle_amr):
                continue

            nodes_data = need_send_suborder.path.get("nodes", []) if isinstance(need_send_suborder.path, dict) else []
            edges_data = need_send_suborder.path.get("edges", []) if isinstance(need_send_suborder.path, dict) else []

            anchor_seq = _resolve_anchor_seq(need_send_suborder, handle_amr, nodes_data) or 0
            ouid_str = str(need_send_suborder.order_update_id)

            with _anchor_lock:
                _last_sent_anchor_seq[sub_id_str] = anchor_seq
                _sent_anchor_history.setdefault(sub_id_str, {})[ouid_str] = anchor_seq

            # Find topic control
            topic_control = TopicControl.objects.filter(
                amr=handle_amr,
                topic_type=TopicControl.TopicType.ORDER,
            ).first()

            msg_header = MsgHeader(
                topic_control=topic_control,
                manufacturer=handle_amr.manufacturer or "SEVT",
                version=handle_amr.version or "2.1.0",
                serial_number=handle_amr.serial_number,
            )

            order_msg = vda_5050_order.Order(
                headerId=msg_header.get_current_header_id_and_increase(),
                timestamp=msg_header.get_current_timestamp_utc(),
                version=msg_header.version,
                manufacturer=msg_header.manufacturer,
                serialNumber=handle_amr.serial_number,
                orderId=str(need_send_suborder.order.id),
                orderUpdateId=need_send_suborder.order_update_id,
                zoneSetId=need_send_suborder.path.get("zoneSetId") if isinstance(need_send_suborder.path, dict) else None,
                nodes=nodes_data,
                edges=edges_data,
            )

            msg_dict = asdict(order_msg)
            if msg_dict.get("zoneSetId") is None:
                msg_dict.pop("zoneSetId", None)

            _register_dispatched_actions(need_send_suborder, handle_amr, msg_dict, self)

            # FIX 2.1: Lock tracking item before pushing it onto the queue
            with _dispatched_lock:
                _dispatched_in_flight.add(sub_id_str)

            try:
                queue_order_2_sent.put(
                    (msg_header.topic, msg_dict, sub_id_str), timeout=0.1
                )
            except queue.Full:
                with _dispatched_lock:
                    _dispatched_in_flight.discard(sub_id_str)
                self.logger.warning("Queue is Full. Retrying next cycle.")
            except Exception as e:
                self.logger.warning(str(e))
                need_send_suborder.status = SubOrder.Status.FAILED
                need_send_suborder.outcome = str(e)
                need_send_suborder.save(update_fields=["status", "outcome"])
                with _dispatched_lock:
                    _dispatched_in_flight.discard(sub_id_str)
                continue


class OrderSendMqtt(MQTTInterfaceWorker):
    def __init__(
        self,
        thread_name="mqtt_send_suborder",
        worker_name=WORKER_NAME,
        loop_sleep_s=0.5,
    ):
        super().__init__(thread_name, worker_name, loop_sleep_s)

    def check_acked(self, entry):
        try:
            suborder = SubOrder.objects.get(id=entry["suborder_id"])
        except SubOrder.DoesNotExist:
            return "DROP"
        if suborder.status == SubOrder.Status.FAILED:
            return "DROP"

        # Check if AMR state in DB has confirmed orderId and orderUpdateId
        handle_amr = AmrVehicle.objects.filter(serial_number=entry.get("serial_number", "")).first()
        if handle_amr:
            if (
                handle_amr.order_id == str(suborder.order.id)
                and handle_amr.order_update_id >= suborder.order_update_id
            ):
                return "ACKED"
        return "PENDING"

    def _resend(self, entry):
        topic = entry["topic"]
        payload_str = entry["payload"]
        suborder_id = entry["suborder_id"]
        now = time.time()
        with _pending_lock:
            if suborder_id in _pending_publishes:
                _pending_publishes[suborder_id]["last_sent"] = now
        entry["last_sent"] = now

        self.logger.info(f"Resending VDA5050 order to {topic} (SubOrder: {suborder_id})")
        success = self.publish(topic, payload_str, qos=1)
        if not success:
            self.logger.warning(f"Resend failed for suborder {suborder_id}")

    def _mark_publish_failed(self, suborder_id, reason):
        try:
            with transaction.atomic():
                suborder = SubOrder.objects.select_for_update().get(id=suborder_id)
                suborder.status = SubOrder.Status.FAILED
                suborder.outcome = reason
                suborder.save(update_fields=["status", "outcome"])
        except SubOrder.DoesNotExist:
            pass
        finally:
            with _pending_lock:
                _pending_publishes.pop(suborder_id, None)
            with _dispatched_lock:
                _dispatched_in_flight.discard(suborder_id)

    def _handle_pending(self):
        now = time.time()
        with _pending_lock:
            items = [(sid, dict(e)) for sid, e in list(_pending_publishes.items())]

        for suborder_id, entry in items:
            ack_status = self.check_acked(entry)

            if ack_status == "ACKED":
                # FIX 1.2: Thread-safe locking using transaction blocks
                with transaction.atomic():
                    try:
                        suborder = SubOrder.objects.select_for_update().get(id=suborder_id)
                        if suborder.status == SubOrder.Status.PENDING:
                            suborder.status = SubOrder.Status.SENT
                            suborder.save(update_fields=["status"])
                    except SubOrder.DoesNotExist:
                        pass
                with _pending_lock:
                    _pending_publishes.pop(suborder_id, None)
                with _dispatched_lock:
                    _dispatched_in_flight.discard(suborder_id)
                continue

            elif ack_status == "DROP":
                with _pending_lock:
                    _pending_publishes.pop(suborder_id, None)
                with _dispatched_lock:
                    _dispatched_in_flight.discard(suborder_id)
                continue

            if now - entry["first_sent"] > SENT_TIMEOUT_SECONDS:
                self._mark_publish_failed(
                    suborder_id, f"Order not accepted within {SENT_TIMEOUT_SECONDS}s"
                )
                continue

            if now - entry["last_sent"] >= RESEND_INTERVAL_SECONDS:
                self._resend(entry)

    def task(self):
        # 1. Process outbound queue
        try:
            topic, msg_dict, sub_id_str = queue_order_2_sent.get_nowait()
            payload_str = json.dumps(msg_dict)
            self.logger.info(f"Publishing VDA5050 Order to {topic} (SubOrder: {sub_id_str})")
            success = self.publish(topic, payload_str, qos=1)
            now = time.time()

            with _pending_lock:
                _pending_publishes[sub_id_str] = {
                    "suborder_id": sub_id_str,
                    "topic": topic,
                    "payload": payload_str,
                    "first_sent": now,
                    "last_sent": now,
                    "serial_number": msg_dict.get("serialNumber", ""),
                }
            queue_order_2_sent.task_done()
        except queue.Empty:
            pass

        # 2. Check and retry pending acknowledgements
        self._handle_pending()


class SubOrderSentTimeoutChecker(WorkerThread):
    def __init__(
        self,
        thread_name="suborder_timeout_checker",
        worker_name=WORKER_NAME,
        loop_sleep_s=2.0,
    ):
        super().__init__(thread_name, worker_name, loop_sleep_s)

    def task(self):
        threshold = timezone.now() - timezone.timedelta(seconds=SENT_TIMEOUT_SECONDS)
        stuck_suborders = SubOrder.objects.filter(
            status=SubOrder.Status.SENT,
            updated_at__lt=threshold,
        )
        for so in stuck_suborders:
            so.status = SubOrder.Status.FAILED
            so.outcome = f"Stuck in SENT execution loop state (> {SENT_TIMEOUT_SECONDS}s)"
            so.save(update_fields=["status", "outcome"])
            self.logger.warning(f"SubOrder {so.id} execution timeout -> FAILED")


#################################################################
# END WORKER DEFINITION
#################################################################

def main():
    thread_sub_order_send_mqtt = OrderSendMqtt()
    thread_sub_order_dispatcher = SubOrderDispatcher()
    thread_sent_timeout = SubOrderSentTimeoutChecker()
    threads = [
        thread_sub_order_send_mqtt,
        thread_sub_order_dispatcher,
        thread_sent_timeout,
    ]

    for thread in threads:
        thread.start()

    _shutdown_done = False

    def _do_shutdown():
        nonlocal _shutdown_done
        if _shutdown_done:
            return
        _shutdown_done = True
        print("\n[acs_order_send] Shutting down...")
        for thread in threads:
            thread.stop()
        for thread in threads:
            try:
                thread.join(timeout=5)
            except Exception:
                pass

    def _signal_handler(signum, frame):
        _do_shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, _signal_handler)
    else:
        signal.signal(signal.SIGTERM, _signal_handler)

    import atexit
    atexit.register(_do_shutdown)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _do_shutdown()


if __name__ == "__main__":
    main()
