import uuid
from django.db import models


class Buffer(models.Model):
    class Status(models.TextChoices):
        EMPTY = "EMPTY", "Empty"
        OCCUPIED = "OCCUPIED", "Occupied"
        RESERVED = "RESERVED", "Reserved"
        ERROR = "ERROR", "Error"

    class BufferType(models.TextChoices):
        PICK = "PICK", "Pick"
        DROP = "DROP", "Drop"
        DUAL = "DUAL", "Dual (Pick/Drop)"
        INSPECTION = "INSPECTION", "Inspection"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    rssid = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=50, choices=BufferType.choices, default=BufferType.DUAL)
    product_model = models.CharField(max_length=100, blank=True, default="")
    process = models.CharField(max_length=100, blank=True, default="")
    role_id = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EMPTY)
    enable = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    node = models.OneToOneField("map.Node", on_delete=models.SET_NULL, null=True, blank=True, related_name="buffer")
    handle_order = models.ForeignKey("acs.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="buffers")
    update_time = models.DateTimeField(auto_now=True)
    last_success_transfer = models.DateTimeField(null=True, blank=True)
    time_gap_btw_transfer = models.DurationField(null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "buffer_station"

    def __str__(self):
        return f"Buffer {self.name} [{self.rssid}] ({self.status})"


class Schedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True, default="")
    map = models.ForeignKey("map.MapBase", on_delete=models.CASCADE, related_name="schedules")
    number_of_amr_need = models.PositiveIntegerField(default=1)
    number_of_active_order = models.PositiveIntegerField(default=0)
    enable = models.BooleanField(default=True)

    class Meta:
        db_table = "buffer_schedule"

    def __str__(self):
        return f"Schedule {self.name} (AMRs needed: {self.number_of_amr_need})"


class ScheduleStop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="stops")
    role_id = models.CharField(max_length=50)
    sequence = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "buffer_schedule_stop"
        ordering = ["sequence"]

    def __str__(self):
        return f"Stop #{self.sequence} for {self.schedule.name} (Role: {self.role_id})"


class ActionOption:
    """Enum types for action options in buffer schedule."""
    class Type(models.TextChoices):
        LOAD = "LOAD", "Load Pallet"
        UNLOAD = "UNLOAD", "Unload Pallet"
        WAIT = "WAIT", "Wait"
        CHARGE = "CHARGE", "Charge"


class StopAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule_stop = models.ForeignKey(ScheduleStop, on_delete=models.CASCADE, related_name="actions")
    action = models.ForeignKey("map.Action", on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "buffer_stop_action"
        ordering = ["sequence"]

    def __str__(self):
        return f"Action #{self.sequence} on Stop {self.schedule_stop_id}"
