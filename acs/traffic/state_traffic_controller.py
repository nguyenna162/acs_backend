import time
import logging
from typing import List, Dict, Optional, Tuple
from .models import RobotPriority
from .state_reservation_manager import default_reservation_manager, StateReservationManager

logger = logging.getLogger("traffic.controller")


class StateTrafficController:
    """Traffic controller managing robot paths and dynamic deadlock avoidance."""

    def __init__(self, reservation_manager: Optional[StateReservationManager] = None):
        self.reservation_manager = reservation_manager or default_reservation_manager

    def request_path_reservation(
        self,
        robot_id: str,
        path_nodes: List[str],
        path_edges: List[str],
        speeds: Optional[List[float]] = None,
        priority: int = RobotPriority.NORMAL,
    ) -> Tuple[bool, int]:
        """Attempts to reserve nodes and edges for the upcoming path.
        Returns (success: bool, reserved_up_to_node_index: int).
        """
        now = time.time()
        current_time = now
        default_speed = 1.0  # m/s
        default_node_wait = 2.0  # seconds on node

        reserved_nodes = 0
        for i, node_id in enumerate(path_nodes):
            node_duration = default_node_wait
            can_res = self.reservation_manager.reserve(
                robot_id=robot_id,
                resource_type="node",
                resource_id=node_id,
                start_time=current_time,
                end_time=current_time + node_duration,
                priority=priority,
            )
            if not can_res:
                logger.warning(f"Traffic contention at node {node_id} for AMR {robot_id}")
                return False, i

            reserved_nodes += 1
            current_time += node_duration

            # Reserve connecting edge if available
            if i < len(path_edges):
                edge_id = path_edges[i]
                edge_duration = 5.0  # estimated transit
                can_res_edge = self.reservation_manager.reserve(
                    robot_id=robot_id,
                    resource_type="edge",
                    resource_id=edge_id,
                    start_time=current_time,
                    end_time=current_time + edge_duration,
                    priority=priority,
                )
                if not can_res_edge:
                    logger.warning(f"Traffic contention on edge {edge_id} for AMR {robot_id}")
                    return False, i

                current_time += edge_duration

        return True, reserved_nodes

    def release_robot_path(self, robot_id: str):
        self.reservation_manager.release(robot_id)


# Singleton
default_traffic_controller = StateTrafficController()
