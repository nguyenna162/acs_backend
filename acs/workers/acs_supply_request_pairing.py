import os
import sys
import time
import logging
from datetime import datetime, timezone
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "acs.settings")
    django.setup()

from acs.models import SupplyRequest, Order
from amr.models import AmrVehicle
from buffer.models import Buffer
from workers.worker_schema_class import WorkerThread
from workers.utilities.graph_distance import default_graph_service

logger = logging.getLogger("workers.acs_supply_request_pairing")


class SupplyRequestPairingWorker(WorkerThread):
    """Pairs Supply Requests with AMRs using Priority Tiers and Dijkstra + SLA deadline tiebreakers."""

    def __init__(self, thread_name="supply_request_pairing", worker_name="acs_supply_pairing", loop_sleep_s=2.0):
        super().__init__(thread_name, worker_name, loop_sleep_s)

    def task(self):
        # 1. Fetch PENDING supply requests
        pending_requests = list(
            SupplyRequest.objects.filter(status=SupplyRequest.Status.PENDING).select_related("buffer")
        )
        if not pending_requests:
            return

        # 2. Fetch idle AMRs
        idle_amrs = list(AmrVehicle.objects.filter(is_online=True, is_idle=True))
        if not idle_amrs:
            return

        # 3. Sort requests into Priority Tiers:
        # Tier 1 (priority >= 8), Tier 2 (priority 4..7), Tier 3 (priority <= 3)
        def sort_key(req: SupplyRequest):
            # Primary sort: negative priority (higher priority first)
            # Secondary sort: SLA deadline (earliest deadline first)
            now = datetime.now(timezone.utc)
            deadline = req.sla_deadline or datetime.max.replace(tzinfo=timezone.utc)
            return (-req.priority, deadline)

        pending_requests.sort(key=sort_key)

        # 4. Pair requests using Tiebreaker: Dijkstra distance from AMR to buffer node
        paired_count = 0
        for req in pending_requests:
            if not idle_amrs:
                break

            target_buffer = req.buffer
            target_node_id = str(target_buffer.node_id) if target_buffer.node_id else ""

            # Score each idle AMR by distance to buffer node
            best_amr = None
            min_distance = float("inf")

            for amr in idle_amrs:
                dist = default_graph_service.compute_distance(amr.last_node_id or "", target_node_id)
                if dist < min_distance:
                    min_distance = dist
                    best_amr = amr

            if best_amr:
                # Create Transport Order
                order_code = f"SUPPLY_{req.line_id}_{int(time.time())}"
                new_order = Order.objects.create(
                    order_id=order_code,
                    order_type=Order.Type.TRANSPORT,
                    status=Order.Status.PENDING,
                    priority=Order.Priority.HIGH if req.priority >= 7 else Order.Priority.NORMAL,
                    target_node=target_buffer.node,
                    description=f"Auto-generated supply order for material {req.material_id} to buffer {target_buffer.name}",
                )

                req.status = SupplyRequest.Status.PAIRED
                req.save(update_fields=["status"])

                idle_amrs.remove(best_amr)
                paired_count += 1
                self.logger.info(
                    f"Paired SupplyRequest {req.id} (Material: {req.material_id}) with AMR {best_amr.serial_number} -> Order {order_code}"
                )


def main():
    worker = SupplyRequestPairingWorker()
    worker.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()
        worker.join(timeout=3)


if __name__ == "__main__":
    main()
