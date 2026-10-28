from django.contrib import admin
from .models import Buffer, Schedule, ScheduleStop, StopAction


@admin.register(Buffer)
class BufferAdmin(admin.ModelAdmin):
    list_display = ["name", "rssid", "type", "status", "enable", "node", "update_time"]
    list_filter = ["status", "type", "enable"]
    search_fields = ["name", "rssid"]


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ["name", "map", "number_of_amr_need", "enable"]
    list_filter = ["enable"]
    search_fields = ["name"]


@admin.register(ScheduleStop)
class ScheduleStopAdmin(admin.ModelAdmin):
    list_display = ["schedule", "role_id", "sequence"]
    list_filter = ["role_id"]


@admin.register(StopAction)
class StopActionAdmin(admin.ModelAdmin):
    list_display = ["schedule_stop", "action", "sequence"]
