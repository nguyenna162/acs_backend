import time
import math
import heapq
import threading
from typing import Dict, List, Tuple, Optional, Any


class GraphDistanceService:
    """Standalone Dijkstra Shortest Path service with heapq and 60-second TTL in-memory cache."""

    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl_seconds = ttl_seconds
        self._graph: Dict[str, List[Tuple[str, float, str]]] = {}  # node_id -> [(neighbor_id, weight, edge_id)]
        self._node_coords: Dict[str, Tuple[float, float, float]] = {}  # node_id -> (x, y, theta)
        self._last_loaded = 0.0
        self._lock = threading.Lock()

    def invalidate_cache(self):
        with self._lock:
            self._last_loaded = 0.0

    def _ensure_graph_loaded(self):
        now = time.time()
        if now - self._last_loaded < self.ttl_seconds and self._graph:
            return

        with self._lock:
            if now - self._last_loaded < self.ttl_seconds and self._graph:
                return

            try:
                from map.models import Node, Edge

                nodes = Node.objects.filter(use_node=True).values("id", "name", "x", "y", "theta")
                node_coords = {str(n["id"]): (float(n["x"]), float(n["y"]), float(n["theta"])) for n in nodes}
                name_to_id = {n["name"]: str(n["id"]) for n in nodes}

                graph: Dict[str, List[Tuple[str, float, str]]] = {str(n["id"]): [] for n in nodes}

                edges = Edge.objects.all().values("id", "start_node_id", "end_node_id", "length", "direction", "max_speed")
                for e in edges:
                    u = str(e["start_node_id"])
                    v = str(e["end_node_id"])
                    length = float(e["length"]) if e["length"] else 1.0

                    if u not in graph:
                        graph[u] = []
                    if v not in graph:
                        graph[v] = []

                    graph[u].append((v, length, str(e["id"])))
                    if e.get("direction") == "BIDIRECTIONAL":
                        graph[v].append((u, length, str(e["id"])))

                self._graph = graph
                self._node_coords = node_coords
                self._last_loaded = now
            except Exception:
                # If database is not ready or tables not yet migrated
                pass

    def compute_distance(self, start_node_id: str, end_node_id: str) -> float:
        """Returns shortest distance between start and end node. Returns inf if unreachable."""
        if start_node_id == end_node_id:
            return 0.0

        self._ensure_graph_loaded()

        if start_node_id not in self._graph or end_node_id not in self._graph:
            # Fallback to Euclidean straight line distance if coords exist
            if start_node_id in self._node_coords and end_node_id in self._node_coords:
                x1, y1, _ = self._node_coords[start_node_id]
                x2, y2, _ = self._node_coords[end_node_id]
                return math.hypot(x2 - x1, y2 - y1)
            return float("inf")

        # Dijkstra algorithm with priority queue
        distances: Dict[str, float] = {start_node_id: 0.0}
        pq = [(0.0, start_node_id)]

        while pq:
            curr_dist, u = heapq.heappop(pq)

            if curr_dist > distances.get(u, float("inf")):
                continue

            if u == end_node_id:
                return curr_dist

            for v, weight, _ in self._graph.get(u, []):
                new_dist = curr_dist + weight
                if new_dist < distances.get(v, float("inf")):
                    distances[v] = new_dist
                    heapq.heappop(pq) if False else None
                    heapq.heappush(pq, (new_dist, v))

        return distances.get(end_node_id, float("inf"))

    def find_shortest_path(self, start_node_id: str, end_node_id: str) -> Tuple[List[str], List[str], float]:
        """Returns (node_ids, edge_ids, total_distance)."""
        if start_node_id == end_node_id:
            return [start_node_id], [], 0.0

        self._ensure_graph_loaded()

        distances: Dict[str, float] = {start_node_id: 0.0}
        previous_node: Dict[str, Optional[str]] = {start_node_id: None}
        previous_edge: Dict[str, Optional[str]] = {}
        pq = [(0.0, start_node_id)]

        while pq:
            curr_dist, u = heapq.heappop(pq)

            if curr_dist > distances.get(u, float("inf")):
                continue

            if u == end_node_id:
                break

            for v, weight, edge_id in self._graph.get(u, []):
                new_dist = curr_dist + weight
                if new_dist < distances.get(v, float("inf")):
                    distances[v] = new_dist
                    previous_node[v] = u
                    previous_edge[v] = edge_id
                    heapq.heappush(pq, (new_dist, v))

        if end_node_id not in distances:
            return [], [], float("inf")

        # Reconstruct path
        path_nodes = []
        path_edges = []
        curr = end_node_id
        while curr:
            path_nodes.append(curr)
            edge = previous_edge.get(curr)
            if edge:
                path_edges.append(edge)
            curr = previous_node.get(curr)

        path_nodes.reverse()
        path_edges.reverse()
        return path_nodes, path_edges, distances[end_node_id]


# Singleton instance
default_graph_service = GraphDistanceService(ttl_seconds=60.0)
