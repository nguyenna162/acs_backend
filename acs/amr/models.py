from django.db import models


class AmrVehicle(models.Model):
    class OperatingMode(models.TextChoices):
        AUTOMATIC = "AUTOMATIC", "Automatic"
        SEMIAUTOMATIC = "SEMIAUTOMATIC", "Semiautomatic"
        MANUAL = "MANUAL", "Manual"
        SERVICE = "SERVICE", "Service"
        TEACHIN = "TEACHIN", "Teachin"

    serial_number = models.CharField(max_length=100, primary_key=True)
    amr_model = models.CharField(max_length=100, default="AMR_LIFT_500")
    interface = models.CharField(max_length=50, default="VDA5050_2.1.0")
    manufacturer = models.CharField(max_length=100, default="SEVT")
    version = models.CharField(max_length=50, default="2.1.0")
    ip_address = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    port = models.PositiveIntegerField(default=1800)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
    is_idle = models.BooleanField(default=True)
    is_used_by_master = models.ForeignKey("acs.OrderMaster", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_amrs")

    # VDA 5050 state fields
    last_node_id = models.CharField(max_length=100, blank=True, default="")
    order_id = models.CharField(max_length=100, blank=True, default="")
    order_update_id = models.BigIntegerField(default=0)
    node_states = models.JSONField(default=list, blank=True)
    edge_states = models.JSONField(default=list, blank=True)
    action_state = models.JSONField(default=list, blank=True)
    loads = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    information = models.JSONField(default=list, blank=True)
    amr_position = models.JSONField(default=dict, blank=True)
    velocity = models.JSONField(default=dict, blank=True)
    battery_state = models.JSONField(default=dict, blank=True)
    safety_state = models.JSONField(default=dict, blank=True)
    driving = models.BooleanField(default=False)
    paused = models.BooleanField(default=False)
    new_base_request = models.BooleanField(default=False)
    operating_mode = models.CharField(max_length=30, choices=OperatingMode.choices, default=OperatingMode.AUTOMATIC)
    zone_set_id = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        db_table = "amr_vehicle"
        indexes = [
            models.Index(fields=["is_online", "is_idle"]),
            models.Index(fields=["order_id"]),
        ]

    def __str__(self):
        status = "ONLINE" if self.is_online else "OFFLINE"
        state = "IDLE" if self.is_idle else "BUSY"
        return f"AMR {self.serial_number} ({status}/{state}) - Mode: {self.operating_mode}"


class TopicControl(models.Model):
    class TopicType(models.TextChoices):
        ORDER = "order", "Order"
        INSTANT_ACTIONS = "instantActions", "Instant Actions"
        STATE = "state", "State"
        CONNECTION = "connection", "Connection"
        VISUALIZATION = "visualization", "Visualization"

    id = models.BigAutoField(primary_key=True)
    topic = models.CharField(max_length=255, unique=True)
    topic_type = models.CharField(max_length=50, choices=TopicType.choices, default=TopicType.ORDER)
    amr = models.ForeignKey(AmrVehicle, on_delete=models.CASCADE, related_name="topics")
    manufacturer = models.CharField(max_length=100, default="SEVT")
    version = models.CharField(max_length=50, default="2.1.0")
    header_id = models.PositiveBigIntegerField(default=0)
    last_call = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "amr_topic_control"

    def __str__(self):
        return f"{self.topic} (AMR: {self.amr_id})"


class AmrStateLog(models.Model):
    id = models.AutoField(primary_key=True)
    serialNumber = models.ForeignKey(AmrVehicle, on_delete=models.CASCADE, related_name="state_logs")
    order_id = models.CharField(max_length=100, blank=True, default="")
    order_update_id = models.BigIntegerField(default=0)
    operating_mode = models.CharField(max_length=50, blank=True, default="")
    node_state = models.JSONField(default=list, blank=True)
    edge_state = models.JSONField(default=list, blank=True)
    action_state = models.JSONField(default=list, blank=True)
    loads = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    information = models.JSONField(default=list, blank=True)
    amr_position = models.JSONField(default=dict, blank=True)
    velocity = models.JSONField(default=dict, blank=True)
    battery_state = models.JSONField(default=dict, blank=True)
    safety_state = models.JSONField(default=dict, blank=True)
    driving = models.BooleanField(default=False)
    paused = models.BooleanField(default=False)
    new_base_request = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "amr_state_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["serialNumber", "created_at"]),
        ]

    def __str__(self):
        return f"StateLog for {self.serialNumber_id} at {self.created_at}"
