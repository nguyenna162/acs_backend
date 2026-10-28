from rest_framework import viewsets
from .models import MapBase, WorldMapLayer, GridMapLayer, ZoneSet, TrafficZone, Node, Edge, Action
from .serializers import (
    MapBaseSerializer,
    WorldMapLayerSerializer,
    GridMapLayerSerializer,
    ZoneSetSerializer,
    TrafficZoneSerializer,
    NodeSerializer,
    EdgeSerializer,
    ActionSerializer,
)


class MapBaseViewSet(viewsets.ModelViewSet):
    """Quản lý các phiên bản bản đồ nhà máy."""
    queryset = MapBase.objects.all().order_by("-created_at")
    serializer_class = MapBaseSerializer


class WorldMapLayerViewSet(viewsets.ModelViewSet):
    queryset = WorldMapLayer.objects.all()
    serializer_class = WorldMapLayerSerializer


class GridMapLayerViewSet(viewsets.ModelViewSet):
    queryset = GridMapLayer.objects.all()
    serializer_class = GridMapLayerSerializer


class ZoneSetViewSet(viewsets.ModelViewSet):
    queryset = ZoneSet.objects.all()
    serializer_class = ZoneSetSerializer


class TrafficZoneViewSet(viewsets.ModelViewSet):
    queryset = TrafficZone.objects.all()
    serializer_class = TrafficZoneSerializer


class NodeViewSet(viewsets.ModelViewSet):
    """Quản lý các Node (điểm dừng, lấy hàng, sạc pin) trên bản đồ."""
    queryset = Node.objects.all().order_by("name")
    serializer_class = NodeSerializer
    filterset_fields = ["map", "type", "use_node"]


class EdgeViewSet(viewsets.ModelViewSet):
    """Quản lý các Edge (đoạn nối chuyển động giữa các node)."""
    queryset = Edge.objects.all()
    serializer_class = EdgeSerializer
    filterset_fields = ["map", "direction"]


class ActionViewSet(viewsets.ModelViewSet):
    """Quản lý danh mục các Action VDA 5050."""
    queryset = Action.objects.all()
    serializer_class = ActionSerializer
