import uuid
from django.db import models
from django.conf import settings


class MapBase(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        DRAFT = "DRAFT", "Draft"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    part = models.CharField(max_length=50, default="CNC_PROD_2G")
    version = models.CharField(max_length=50, default="1.0.0")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    description = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "map_base"

    def __str__(self):
        return f"{self.name} v{self.version} ({self.part})"


class WorldMapLayer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    map = models.OneToOneField(MapBase, on_delete=models.CASCADE, related_name="world_layer")
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="maps/world/", null=True, blank=True)
    x_origin = models.FloatField(default=0.0)
    y_origin = models.FloatField(default=0.0)
    resolution = models.FloatField(default=0.05)  # meters per pixel
    resize = models.FloatField(default=1.0)
    opacity = models.FloatField(default=1.0)
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "map_world_layer"


class GridMapLayer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    map = models.OneToOneField(MapBase, on_delete=models.CASCADE, related_name="grid_layer")
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="maps/grid/", null=True, blank=True)
    x_set_background = models.IntegerField(default=0)
    y_set_background = models.IntegerField(default=0)
    resize = models.FloatField(default=1.0)
    opacity = models.FloatField(default=1.0)

    class Meta:
        db_table = "map_grid_layer"


class ZoneSet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    map = models.ForeignKey(MapBase, on_delete=models.CASCADE, related_name="zone_sets")
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True, default="")
    version = models.CharField(max_length=50, default="1.0")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "map_zone_set"

    def __str__(self):
        return f"ZoneSet {self.name} ({self.version})"


class TrafficZone(models.Model):
    class ZoneType(models.TextChoices):
        INTERSECTION = "INTERSECTION", "Intersection"
        AISLE = "AISLE", "Aisle"
        CHARGING_AREA = "CHARGING_AREA", "Charging Area"
        BUFFER_AREA = "BUFFER_AREA", "Buffer Area"
        RESTRICTED = "RESTRICTED", "Restricted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone_set = models.ForeignKey(ZoneSet, on_delete=models.CASCADE, related_name="traffic_zones")
    map = models.ForeignKey(MapBase, on_delete=models.CASCADE, related_name="traffic_zones")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=ZoneType.choices, default=ZoneType.AISLE)
    description = models.CharField(max_length=255, blank=True, default="")
    max_occupancy = models.PositiveIntegerField(default=1)
    priority = models.PositiveIntegerField(default=1)
    max_speed = models.FloatField(default=1.5)

    class Meta:
        db_table = "map_traffic_zone"

    def __str__(self):
        return f"TrafficZone {self.name} (max: {self.max_occupancy})"


class Zone(models.Model):
    """Legacy zone model for compatibility."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone_id = models.CharField(max_length=50)
    zone_name = models.CharField(max_length=100)
    pos_x = models.FloatField(default=0.0)
    pos_y = models.FloatField(default=0.0)
    size_x = models.FloatField(default=0.0)
    size_y = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    aligo_metadata = models.JSONField(default=dict, blank=True)
    map = models.ForeignKey(MapBase, on_delete=models.CASCADE, related_name="legacy_zones")
    zone_set = models.ForeignKey(ZoneSet, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "map_zone_legacy"


class Node(models.Model):
    class NodeTypeChoice(models.TextChoices):
        TRANSIT = "TRANSIT", "Transit"
        PICK = "PICK", "Pick"
        DROP = "DROP", "Drop"
        CHARGE = "CHARGE", "Charge"
        PARK = "PARK", "Park"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    map = models.ForeignKey(MapBase, on_delete=models.CASCADE, related_name="nodes")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=NodeTypeChoice.choices, default=NodeTypeChoice.TRANSIT)
    description = models.CharField(max_length=255, blank=True, default="")
    x = models.FloatField()
    y = models.FloatField()
    theta = models.FloatField(default=0.0)
    allow_deviation_xy = models.FloatField(default=0.05)
    allow_deviation_theta = models.FloatField(default=0.05)
    use_node = models.BooleanField(default=True)
    is_init = models.BooleanField(default=False)
    is_extended = models.BooleanField(default=False)
    traffic_zone = models.ForeignKey(TrafficZone, on_delete=models.SET_NULL, null=True, blank=True, related_name="nodes")
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name="nodes")

    class Meta:
        db_table = "map_node"
        indexes = [
            models.Index(fields=["map", "use_node"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"Node {self.name} ({self.x:.2f}, {self.y:.2f})"


class Edge(models.Model):
    class DirectionChoice(models.TextChoices):
        FORWARD = "FORWARD", "Forward"
        REVERSE = "REVERSE", "Reverse"
        BIDIRECTIONAL = "BIDIRECTIONAL", "Bidirectional"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    map = models.ForeignKey(MapBase, on_delete=models.CASCADE, related_name="edges")
    start_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="outgoing_edges")
    end_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="incoming_edges")
    max_speed = models.FloatField(default=1.2)
    orientation = models.FloatField(default=0.0)
    max_rotation_speed = models.FloatField(default=0.5)
    length = models.FloatField(default=1.0)
    orientation_type = models.CharField(max_length=50, default="TANGENTIAL")
    direction = models.CharField(max_length=20, choices=DirectionChoice.choices, default=DirectionChoice.FORWARD)
    rotation_allowed = models.BooleanField(default=True)
    trajectory = models.JSONField(default=dict, blank=True)
    traffic_zone = models.ForeignKey(TrafficZone, on_delete=models.SET_NULL, null=True, blank=True, related_name="edges")
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name="edges")
    name = models.CharField(max_length=100, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "map_edge"
        indexes = [
            models.Index(fields=["map", "start_node", "end_node"]),
        ]

    def __str__(self):
        return f"Edge {self.start_node.name} -> {self.end_node.name} ({self.length:.2f}m)"


class Action(models.Model):
    class Type(models.TextChoices):
        CHARGING = "CHARGING", "Charging"
        LIFT = "LIFT", "Lift Pallet"
        DROP = "DROP", "Drop Pallet"
        SCAN = "SCAN", "Scan QR/Barcode"
        WAIT = "WAIT", "Wait"
        INIT_POSITION = "INIT_POSITION", "Init Position"

    class BlockingType(models.TextChoices):
        NONE = "NONE", "None"
        SOFT = "SOFT", "Soft"
        HARD = "HARD", "Hard"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=50, choices=Type.choices)
    blocking_type = models.CharField(max_length=20, choices=BlockingType.choices, default=BlockingType.NONE)
    parameters = models.JSONField(default=dict, blank=True)
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "map_action"

    def __str__(self):
        return f"Action {self.type} ({self.blocking_type})"


class ActionOnNode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="actions")

    class Meta:
        db_table = "map_action_on_node"
        unique_together = ("action", "node")


class ActionOnEdge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    edge = models.ForeignKey(Edge, on_delete=models.CASCADE, related_name="actions")

    class Meta:
        db_table = "map_action_on_edge"
        unique_together = ("action", "edge")
