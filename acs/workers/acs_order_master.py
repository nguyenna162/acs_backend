import os
import sys
import time
import logging
import django

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "acs.settings")
    django.setup()

from acs.models import Order, OrderMaster, SubOrder
from amr.models import AmrVehicle
from workers.worker_schema_class import WorkerThread
from workers.utilities.graph_distance import default_graph_service
from traffic.fleet_scheduler import FleetScheduler
from traffic.models import FleetTask, RobotPriority

logger = logging.getLogger("workers.acs_order_master")
MAX_CONCURRENT_PROCESSING_ORDERS = 10


class OrderMasterProcessor(WorkerThread):
    """FIFO processing of PENDING orders based on created_at, with concurrency limit."""

    def __init__(self, thread_name="order_master_processor", worker_name="acs_order_master", loop_sleep_s=1.0):
        super().__init__(thread_name, worker_name, loop_sleep_s)
        self.scheduler = FleetScheduler(default_graph_service)

    def task(self):
        # 1. Check current concurrency level
        active_count = OrderMaster.objects.filter(status=OrderMaster.Status.PROCESSING).count()
        if active_count >= MAX_CONCURRENT_PROCESSING_ORDERS:
            return

        available_slots = MAX_CONCURRENT_PROCESSING_ORDERS - active_count

        # 2. Query PENDING orders in FIFO order (created_at asc)
        pending_orders = list(
            Order.objects.filter(status=Order.Status.PENDING)
            .order_by("created_at")[:available_slots]
        )
        if not pending_orders:
            return

        # 3. Find available idle AMRs
        idle_amrs = list(AmrVehicle.objects.filter(is_online=True, is_idle=True))
        if not idle_amrs:
            return

        # 4. Formulate fleet scheduling tasks
        tasks = []
        order_map = {}
        for o in pending_orders:
            src = str(o.source_node_id) if o.source_node_id else ""
            tgt = str(o.target_node_id) if o.target_node_id else ""
            task = FleetTask(
                task_id=str(o.id),
                order_id=o.order_id,
                source_node_id=src,
                target_node_id=tgt,
                priority=RobotPriority.HIGH if o.priority == Order.Priority.URGENT else RobotPriority.NORMAL,
            )
            tasks.append(task)
            order_map[task.task_id] = o

        # 5. Run Hungarian Algorithm / greedy scheduler
        result = self.scheduler.schedule(idle_amrs, tasks)

        # 6. Bind assignments and instantiate OrderMaster & SubOrders
        for assign in result.assignments:
            order = order_map.get(assign.task_id)
            if not order:
                continue

            amr = AmrVehicle.objects.filter(serial_number=assign.robot_serial).first()
            if not amr:
                continue

            # Create OrderMaster
            master = OrderMaster.objects.create(
                name=f"Master_{order.order_id}_{amr.serial_number}",
                status=OrderMaster.Status.PROCESSING,
            )

            # Assign AMR
            amr.is_idle = False
            amr.is_used_by_master = master
            amr.save(update_fields=["is_idle", "is_used_by_master"])

            # Compute shortest path via Dijkstra
            start_node = amr.last_node_id or (str(order.source_node_id) if order.source_node_id else "")
            target_node = str(order.target_node_id) if order.target_node_id else start_node

            path_nodes, path_edges, total_dist = default_graph_service.find_shortest_path(start_node, target_node)

            # Build VDA 5050 node/edge payload
            nodes_payload = []
            for seq, nid in enumerate(path_nodes):
                nodes_payload.append({
                    "nodeId": nid,
                    "sequenceId": seq * 2,
                    "released": True,
                    "actions": [],
                })

            edges_payload = []
            for seq, eid in enumerate(path_edges):
                edges_payload.append({
                    "edgeId": eid,
                    "sequenceId": seq * 2 + 1,
                    "released": True,
                    "startNodeId": path_nodes[seq],
                    "endNodeId": path_nodes[seq + 1],
                    "actions": [],
                })

            # Create SubOrder
            SubOrder.objects.create(
                order=order,
                order_master=master,
                order_update_id=0,
                path={"nodes": nodes_payload, "edges": edges_payload},
                status=SubOrder.Status.PENDING,
            )

            # Update Order status
            order.status = Order.Status.PROCESSING
            order.save(update_fields=["status"])
            self.logger.info(f"Scheduled Order {order.order_id} to AMR {amr.serial_number}")


def main():
    processor = OrderMasterProcessor()
    processor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        processor.stop()
        processor.join(timeout=3)


if __name__ == "__main__":
    main()
