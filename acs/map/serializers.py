from rest_framework import serializers
from .models import (
    MapBase,
    WorldMapLayer,
    GridMapLayer,
    ZoneSet,
    TrafficZone,
    Zone,
    Node,
    Edge,
    Action,
    ActionOnNode,
    ActionOnEdge,
)


class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = "__all__"


class ActionOnNodeSerializer(serializers.ModelSerializer):
    action_detail = ActionSerializer(source="action", read_only=True)

    class Meta:
        model = ActionOnNode
        fields = "__all__"


class ActionOnEdgeSerializer(serializers.ModelSerializer):
    action_detail = ActionSerializer(source="action", read_only=True)

    class Meta:
        model = ActionOnEdge
        fields = "__all__"


class NodeSerializer(serializers.ModelSerializer):
    actions = ActionOnNodeSerializer(many=True, read_only=True)
    map_name = serializers.CharField(source="map.name", read_only=True)

    class Meta:
        model = Node
        fields = "__all__"


class EdgeSerializer(serializers.ModelSerializer):
    actions = ActionOnEdgeSerializer(many=True, read_only=True)
    start_node_name = serializers.CharField(source="start_node.name", read_only=True)
    end_node_name = serializers.CharField(source="end_node.name", read_only=True)

    class Meta:
        model = Edge
        fields = "__all__"


class TrafficZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficZone
        fields = "__all__"


class ZoneSetSerializer(serializers.ModelSerializer):
    traffic_zones = TrafficZoneSerializer(many=True, read_only=True)

    class Meta:
        model = ZoneSet
        fields = "__all__"


class WorldMapLayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorldMapLayer
        fields = "__all__"


class GridMapLayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = GridMapLayer
        fields = "__all__"


class MapBaseSerializer(serializers.ModelSerializer):
    world_layer = WorldMapLayerSerializer(read_only=True)
    grid_layer = GridMapLayerSerializer(read_only=True)

    class Meta:
        model = MapBase
        fields = "__all__"
