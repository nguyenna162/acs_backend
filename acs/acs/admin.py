from django.contrib import admin
from .models import Order, OrderMaster, SubOrder, SupplyRequest, ActionDispatch, Log


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_id", "order_type", "status", "priority", "source_node", "target_node", "created_at"]
    list_filter = ["status", "order_type", "priority"]
    search_fields = ["order_id", "description"]


@admin.register(OrderMaster)
class OrderMasterAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "created_at", "updated_at"]
    list_filter = ["status"]
    search_fields = ["name"]


@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "order_master", "order_update_id", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["id", "order__order_id"]


@admin.register(SupplyRequest)
class SupplyRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "line_id", "buffer", "material_id", "priority", "status", "sla_deadline"]
    list_filter = ["status", "priority", "line_id"]
    search_fields = ["material_id", "line_id"]


@admin.register(ActionDispatch)
class ActionDispatchAdmin(admin.ModelAdmin):
    list_display = ["id", "sub_order", "order", "amr", "action_type", "blocking_type", "created_at"]
    list_filter = ["action_type", "blocking_type"]
    search_fields = ["id", "amr__serial_number"]


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ["id", "level", "module", "message", "created_at"]
    list_filter = ["level", "module"]
    search_fields = ["message", "module"]
