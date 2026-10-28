from django.contrib import admin
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


@admin.register(MapBase)
class MapBaseAdmin(admin.ModelAdmin):
    list_display = ["name", "part", "version", "status", "created_at"]
    list_filter = ["status", "part"]
    search_fields = ["name"]


@admin.register(WorldMapLayer)
class WorldMapLayerAdmin(admin.ModelAdmin):
    list_display = ["map", "name", "resolution", "resize", "opacity"]


@admin.register(GridMapLayer)
class GridMapLayerAdmin(admin.ModelAdmin):
    list_display = ["map", "name", "x_set_background", "y_set_background"]


@admin.register(ZoneSet)
class ZoneSetAdmin(admin.ModelAdmin):
    list_display = ["name", "map", "version", "is_active"]
    list_filter = ["is_active"]


@admin.register(TrafficZone)
class TrafficZoneAdmin(admin.ModelAdmin):
    list_display = ["name", "map", "type", "max_occupancy", "priority", "max_speed"]
    list_filter = ["type"]
    search_fields = ["name"]


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ["name", "map", "type", "x", "y", "theta", "use_node", "traffic_zone"]
    list_filter = ["type", "use_node", "map"]
    search_fields = ["name"]


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    list_display = ["name", "map", "start_node", "end_node", "length", "max_speed", "direction"]
    list_filter = ["direction", "map"]
    search_fields = ["name", "start_node__name", "end_node__name"]


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ["type", "blocking_type", "description"]
    list_filter = ["type", "blocking_type"]
