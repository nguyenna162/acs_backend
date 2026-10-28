from rest_framework import viewsets
from .models import Buffer, Schedule, ScheduleStop, StopAction
from .serializers import BufferSerializer, ScheduleSerializer, ScheduleStopSerializer, StopActionSerializer


class BufferViewSet(viewsets.ModelViewSet):
    """Quản lý các trạm đệm (Buffer / Bục giao nhận hàng)."""
    queryset = Buffer.objects.all().order_by("name")
    serializer_class = BufferSerializer
    filterset_fields = ["status", "type", "enable"]


class ScheduleViewSet(viewsets.ModelViewSet):
    """Lập lịch trình điểm dừng phục vụ ca sản xuất."""
    queryset = Schedule.objects.all().order_by("name")
    serializer_class = ScheduleSerializer


class ScheduleStopViewSet(viewsets.ModelViewSet):
    queryset = ScheduleStop.objects.all().order_by("sequence")
    serializer_class = ScheduleStopSerializer


class StopActionViewSet(viewsets.ModelViewSet):
    queryset = StopAction.objects.all().order_by("sequence")
    serializer_class = StopActionSerializer
