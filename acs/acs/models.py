import uuid
from django.db import models


class OrderMaster(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "acs_order_master"
        ordering = ["-created_at"]

    def __str__(self):
        return f"OrderMaster {self.name} ({self.status})"


class Order(models.Model):
    class Type(models.TextChoices):
        TRANSPORT = "TRANSPORT", "Transport"
        CHARGE = "CHARGE", "Charge"
        PARK = "PARK", "Park"
        MAINTENANCE = "MAINTENANCE", "Maintenance"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=100, unique=True)
    order_type = models.CharField(max_length=20, choices=Type.choices, default=Type.TRANSPORT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    source_node = models.ForeignKey("map.Node", on_delete=models.SET_NULL, null=True, blank=True, related_name="source_orders")
    target_node = models.ForeignKey("map.Node", on_delete=models.SET_NULL, null=True, blank=True, related_name="target_orders")
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "acs_order"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["order_id"]),
        ]

    def __str__(self):
        return f"Order {self.order_id} [{self.order_type}] - {self.status}"


class SubOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="suborders")
    order_master = models.ForeignKey(OrderMaster, on_delete=models.SET_NULL, null=True, blank=True, related_name="suborders")
    order_update_id = models.BigIntegerField(default=0)
    path = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    outcome = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "acs_sub_order"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["order", "order_update_id"]),
        ]

    def __str__(self):
        return f"SubOrder {self.id} (Order: {self.order.order_id}) - {self.status}"


class SupplyRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAIRED = "PAIRED", "Paired"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    line_id = models.CharField(max_length=64)
    buffer = models.ForeignKey("buffer.Buffer", on_delete=models.CASCADE, related_name="supply_requests")
    material_id = models.CharField(max_length=64)
    priority = models.IntegerField(default=1)  # 1 to 10
    sla_deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "acs_supply_request"
        ordering = ["-priority", "sla_deadline", "created_at"]

    def __str__(self):
        return f"SupplyRequest {self.material_id} for Line {self.line_id} ({self.status})"


class ActionDispatch(models.Model):
    id = models.CharField(max_length=128, primary_key=True)  # VDA 5050 actionId
    sub_order = models.ForeignKey(SubOrder, on_delete=models.CASCADE, related_name="dispatched_actions")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="dispatched_actions")
    amr = models.ForeignKey("amr.AmrVehicle", on_delete=models.CASCADE, related_name="dispatched_actions")
    action_type = models.CharField(max_length=64)
    blocking_type = models.CharField(max_length=16, default="NONE")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "acs_action_dispatch"

    def __str__(self):
        return f"ActionDispatch {self.id} ({self.action_type})"


class Log(models.Model):
    id = models.BigAutoField(primary_key=True)
    level = models.CharField(max_length=16, default="INFO")
    module = models.CharField(max_length=64)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "acs_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.created_at}] [{self.level}] {self.module}: {self.message[:60]}"
