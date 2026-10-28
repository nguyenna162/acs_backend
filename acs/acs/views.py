import os
import time
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Order, OrderMaster, SubOrder, SupplyRequest, ActionDispatch, Log
from .serializers import (
    OrderSerializer,
    OrderMasterSerializer,
    SubOrderSerializer,
    SupplyRequestSerializer,
    ActionDispatchSerializer,
    LogSerializer,
    FindPathInputSerializer,
    DispatchAMRInputSerializer,
)
from map.models import Node, Edge
from amr.models import AmrVehicle
from workers.utilities.graph_distance import default_graph_service


class OrderViewSet(viewsets.ModelViewSet):
    """Quản lý các đơn vận chuyển AMR trong nhà máy."""
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderSerializer
    filterset_fields = ["status", "order_type", "priority"]


class OrderMasterViewSet(viewsets.ReadOnlyModelViewSet):
    """Xem xét các phiên điều phối Master điều hành robot."""
    queryset = OrderMaster.objects.all().order_by("-created_at")
    serializer_class = OrderMasterSerializer


class SubOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Chi tiết từng phân đoạn SubOrder theo tiêu chuẩn VDA 5050."""
    queryset = SubOrder.objects.all().order_by("-created_at")
    serializer_class = SubOrderSerializer


class SupplyRequestViewSet(viewsets.ModelViewSet):
    """Quản lý nhu cầu cấp phôi / vật tư dây chuyền sản xuất Aligo."""
    queryset = SupplyRequest.objects.all().order_by("-created_at")
    serializer_class = SupplyRequestSerializer


class LogViewSet(viewsets.ReadOnlyModelViewSet):
    """Tra cứu nhật ký sự kiện hệ thống."""
    queryset = Log.objects.all().order_by("-created_at")
    serializer_class = LogSerializer


@extend_schema(
    request=FindPathInputSerializer,
    responses={200: dict},
    description="Tìm lộ trình tối ưu VDA 5050 giữa 2 Node sử dụng giải thuật Dijkstra kết hợp Cache Graph."
)
@api_view(["POST"])
def find_path_vda(request):
    serializer = FindPathInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    start_node_id = serializer.validated_data["start_node_id"]
    target_node_id = serializer.validated_data["target_node_id"]

    path_nodes, path_edges, total_dist = default_graph_service.find_shortest_path(start_node_id, target_node_id)

    if not path_nodes:
        return Response(
            {"error": "Không tìm thấy lộ trình giữa 2 Node chỉ định", "reachable": False},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Format nodes & edges into VDA 5050 format
    vda_nodes = []
    for idx, nid in enumerate(path_nodes):
        node_obj = Node.objects.filter(id=nid).first()
        vda_nodes.append({
            "nodeId": nid,
            "sequenceId": idx * 2,
            "released": True,
            "nodePosition": {
                "x": node_obj.x if node_obj else 0.0,
                "y": node_obj.y if node_obj else 0.0,
                "theta": node_obj.theta if node_obj else 0.0,
            } if node_obj else None,
            "actions": [],
        })

    vda_edges = []
    for idx, eid in enumerate(path_edges):
        edge_obj = Edge.objects.filter(id=eid).first()
        vda_edges.append({
            "edgeId": eid,
            "sequenceId": idx * 2 + 1,
            "released": True,
            "startNodeId": path_nodes[idx],
            "endNodeId": path_nodes[idx + 1],
            "maxSpeed": edge_obj.max_speed if edge_obj else 1.2,
            "actions": [],
        })

    return Response({
        "reachable": True,
        "total_distance_m": round(total_dist, 2),
        "node_count": len(path_nodes),
        "vda_path": {
            "nodes": vda_nodes,
            "edges": vda_edges,
        },
    })


@extend_schema(
    request=DispatchAMRInputSerializer,
    responses={201: OrderSerializer},
    description="Tạo lệnh điều xe AMR đến node hoặc vận chuyển hàng giữa 2 điểm."
)
@api_view(["POST"])
def dispatch_amr(request):
    serializer = DispatchAMRInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    order_code = f"ORD_{int(time.time())}"
    source_node = None
    target_node = None

    if data.get("source_node_id"):
        source_node = Node.objects.filter(id=data["source_node_id"]).first()
    if data.get("target_node_id"):
        target_node = Node.objects.filter(id=data["target_node_id"]).first()

    order = Order.objects.create(
        order_id=order_code,
        order_type=data.get("order_type", Order.Type.TRANSPORT),
        priority=data.get("priority", Order.Priority.NORMAL),
        status=Order.Status.PENDING,
        source_node=source_node,
        target_node=target_node,
        description=data.get("description", ""),
    )

    return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@extend_schema(
    responses={200: dict},
    description="Tra cứu nội dung file nhật ký vận hành acs_system.log (hỗ trợ log đã chuẩn hóa sang tiếng Anh)."
)
@api_view(["GET"])
def system_logs_file(request):
    """Tra cứu trực tiếp nội dung file nhật ký hệ thống (mặc định lấy log đã chuẩn hóa)."""
    raw = request.GET.get("raw", "false").lower() in ("true", "1")
    formatted_path = os.path.join(os.path.dirname(__file__), "..", "logs", "acs_formatted.log")
    raw_path = os.path.join(os.path.dirname(__file__), "..", "logs", "acs_system.log")

    log_file_path = raw_path if raw or not os.path.exists(formatted_path) else formatted_path
    lines_count = int(request.GET.get("lines", 100))

    if not os.path.exists(log_file_path):
        return Response({"logs": [], "message": "Log file does not exist yet.", "is_formatted": False})

    with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
        all_lines = [line.rstrip("\r\n") for line in f.readlines()]
        tail = all_lines[-lines_count:]

    return Response({
        "total_lines": len(all_lines),
        "returned_lines": len(tail),
        "is_formatted": log_file_path == formatted_path,
        "logs": tail,
    })


@extend_schema(
    responses={200: dict},
    description="Cung cấp dữ liệu đo xa telemetry thời gian thực của toàn bộ đội robot AMR."
)
@api_view(["GET"])
def robot_telemetry_stream(request):
    """Endpoint cung cấp dòng dữ liệu đo xa telemetry của AMR cho Web/Client."""
    vehicles = AmrVehicle.objects.all()
    data = []
    for v in vehicles:
        data.append({
            "serial_number": v.serial_number,
            "amr_model": v.amr_model,
            "is_online": v.is_online,
            "is_idle": v.is_idle,
            "operating_mode": v.operating_mode,
            "order_id": v.order_id,
            "order_update_id": v.order_update_id,
            "last_node_id": v.last_node_id,
            "driving": v.driving,
            "paused": v.paused,
            "battery_state": v.battery_state,
            "amr_position": v.amr_position,
            "velocity": v.velocity,
            "loads": v.loads,
            "errors": v.errors,
            "last_heartbeat": v.last_heartbeat.isoformat() if v.last_heartbeat else None,
        })
    return Response({"telemetry": data, "count": len(data), "timestamp": time.time()})

