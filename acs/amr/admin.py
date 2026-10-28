from django.contrib import admin
from .models import AmrVehicle, TopicControl, AmrStateLog


@admin.register(AmrVehicle)
class AmrVehicleAdmin(admin.ModelAdmin):
    list_display = ["serial_number", "amr_model", "manufacturer", "is_online", "is_idle", "operating_mode", "last_node_id", "order_id", "last_heartbeat"]
    list_filter = ["is_online", "is_idle", "operating_mode", "manufacturer"]
    search_fields = ["serial_number", "amr_model"]


@admin.register(TopicControl)
class TopicControlAdmin(admin.ModelAdmin):
    list_display = ["topic", "topic_type", "amr", "header_id", "last_call"]
    list_filter = ["topic_type"]
    search_fields = ["topic", "amr__serial_number"]


@admin.register(AmrStateLog)
class AmrStateLogAdmin(admin.ModelAdmin):
    list_display = ["id", "serialNumber", "order_id", "order_update_id", "operating_mode", "driving", "created_at"]
    list_filter = ["operating_mode", "driving"]
    search_fields = ["serialNumber__serial_number", "order_id"]
