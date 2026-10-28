import os
import sys
import pytest

# Ensure acs is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "acs")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "acs.settings")

import django
django.setup()

from map.models import Node, Edge, MapBase
from amr.models import AmrVehicle
from acs.models import Order
from workers.utilities.graph_distance import GraphDistanceService
from traffic.fleet_scheduler import FleetScheduler
from traffic.models import FleetTask, RobotPriority
from traffic.state_reservation_manager import StateReservationManager


def test_dijkstra_shortest_path():
    service = GraphDistanceService(ttl_seconds=1.0)
    service.invalidate_cache()

    nodes = list(Node.objects.filter(use_node=True))
    assert len(nodes) >= 2

    start_node = nodes[0]
    end_node = nodes[1]

    path_nodes, path_edges, dist = service.find_shortest_path(str(start_node.id), str(end_node.id))
    assert len(path_nodes) > 0
    assert dist >= 0.0
    print(f"Path from {start_node.name} to {end_node.name}: {dist:.2f}m")


def test_fleet_scheduler_hungarian():
    scheduler = FleetScheduler()
    amrs = list(AmrVehicle.objects.all())
    nodes = list(Node.objects.all())

    tasks = [
        FleetTask(
            task_id="T01",
            order_id="ORD_001",
            source_node_id=str(nodes[3].id),
            target_node_id=str(nodes[4].id),
            priority=RobotPriority.HIGH,
        ),
        FleetTask(
            task_id="T02",
            order_id="ORD_002",
            source_node_id=str(nodes[5].id),
            target_node_id=str(nodes[6].id),
            priority=RobotPriority.NORMAL,
        ),
    ]

    res = scheduler.schedule(amrs[:2], tasks)
    assert len(res.assignments) == 2
    assert res.total_cost >= 0.0
    print(f"Scheduler result: {res.algorithm_used}, Total cost: {res.total_cost:.2f}")


def test_state_reservation_manager():
    import time
    manager = StateReservationManager()
    now = time.time()
    # Reserve node N1 from now+10 to now+20
    ok1 = manager.reserve("AMR_001", "node", "N1", start_time=now + 10.0, end_time=now + 20.0, priority=5)
    assert ok1 is True

    # Same time window by another AMR with lower priority should fail
    ok2 = manager.reserve("AMR_002", "node", "N1", start_time=now + 12.0, end_time=now + 18.0, priority=3)
    assert ok2 is False

    # Non-overlapping time window should succeed
    ok3 = manager.reserve("AMR_002", "node", "N1", start_time=now + 25.0, end_time=now + 35.0, priority=3)
    assert ok3 is True
    print("State reservation manager test passed!")


if __name__ == "__main__":
    test_dijkstra_shortest_path()
    test_fleet_scheduler_hungarian()
    test_state_reservation_manager()
    print("All tests passed successfully!")
