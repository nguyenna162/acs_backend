import logging
from typing import List, Dict, Optional, Any
import numpy as np

try:
    from scipy.optimize import linear_sum_assignment
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from .models import FleetTask, FleetAssignment, FleetSchedulerResult
from workers.utilities.graph_distance import default_graph_service

logger = logging.getLogger("traffic.fleet_scheduler")


class FleetScheduler:
    """Fleet Scheduler assigning idle AMRs to pending tasks using Hungarian Algorithm."""

    def __init__(self, graph_service=None):
        self.graph_service = graph_service or default_graph_service

    def schedule(self, idle_amrs: List[Any], tasks: List[FleetTask]) -> FleetSchedulerResult:
        if not idle_amrs or not tasks:
            return FleetSchedulerResult(
                assignments=[],
                unassigned_robots=[getattr(a, "serial_number", str(a)) for a in idle_amrs],
                unassigned_tasks=[t.task_id for t in tasks],
                total_cost=0.0,
                algorithm_used="NONE",
            )

        num_amrs = len(idle_amrs)
        num_tasks = len(tasks)

        # Build cost matrix: cost_matrix[i][j] = distance from AMR_i current position to Task_j source node
        cost_matrix = np.zeros((num_amrs, num_tasks), dtype=float)

        for i, amr in enumerate(idle_amrs):
            amr_node = getattr(amr, "last_node_id", "")
            for j, task in enumerate(tasks):
                dist = self.graph_service.compute_distance(amr_node, task.source_node_id)
                if np.isinf(dist):
                    dist = 10000.0  # High penalty for disconnected nodes

                # Priority bonus: higher priority lowers effective cost
                priority_discount = task.priority * 1.5
                effective_cost = max(0.1, dist - priority_discount)
                cost_matrix[i, j] = effective_cost

        # Execute assignment
        if HAS_SCIPY:
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            alg_name = "HUNGARIAN"
        else:
            # Fallback Greedy Assignment
            logger.warning("SciPy not available, falling back to Greedy Assignment")
            row_ind, col_ind = self._greedy_assignment(cost_matrix)
            alg_name = "GREEDY_FALLBACK"

        assignments: List[FleetAssignment] = []
        assigned_robots = set()
        assigned_tasks = set()
        total_cost = 0.0

        for r, c in zip(row_ind, col_ind):
            cost = float(cost_matrix[r, c])
            amr = idle_amrs[r]
            task = tasks[c]
            robot_serial = getattr(amr, "serial_number", str(amr))

            assignments.append(
                FleetAssignment(
                    robot_serial=robot_serial,
                    task_id=task.task_id,
                    order_id=task.order_id,
                    cost=cost,
                )
            )
            assigned_robots.add(robot_serial)
            assigned_tasks.add(task.task_id)
            total_cost += cost

        unassigned_robots = [
            getattr(a, "serial_number", str(a))
            for a in idle_amrs
            if getattr(a, "serial_number", str(a)) not in assigned_robots
        ]
        unassigned_tasks = [t.task_id for t in tasks if t.task_id not in assigned_tasks]

        return FleetSchedulerResult(
            assignments=assignments,
            unassigned_robots=unassigned_robots,
            unassigned_tasks=unassigned_tasks,
            total_cost=total_cost,
            algorithm_used=alg_name,
        )

    def _greedy_assignment(self, cost_matrix: np.ndarray):
        rows, cols = cost_matrix.shape
        row_ind = []
        col_ind = []
        used_rows = set()
        used_cols = set()

        flat_indices = np.argsort(cost_matrix, axis=None)
        for idx in flat_indices:
            r = idx // cols
            c = idx % cols
            if r not in used_rows and c not in used_cols:
                row_ind.append(r)
                col_ind.append(c)
                used_rows.add(r)
                used_cols.add(c)
                if len(used_rows) == min(rows, cols):
                    break

        return np.array(row_ind), np.array(col_ind)
