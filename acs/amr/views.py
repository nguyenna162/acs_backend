from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AmrVehicle, TopicControl, AmrStateLog
from .serializers import AmrVehicleSerializer, TopicControlSerializer, AmrStateLogSerializer


class AmrVehicleViewSet(viewsets.ModelViewSet):
    """Quản lý các phương tiện AMR và trạng thái vận hành."""
    queryset = AmrVehicle.objects.all().order_by("serial_number")
    serializer_class = AmrVehicleSerializer

    @action(detail=True, methods=["post"])
    def reset_status(self, request, pk=None):
        amr = self.get_object()
        amr.is_idle = True
        amr.is_used_by_master = None
        amr.order_id = ""
        amr.order_update_id = 0
        amr.driving = False
        amr.paused = False
        amr.new_base_request = False
        amr.save()
        return Response({"status": f"AMR {amr.serial_number} has been reset to IDLE."})

    @action(detail=True, methods=["post"])
    def toggle_pause(self, request, pk=None):
        amr = self.get_object()
        amr.paused = not amr.paused
        amr.save()
        return Response({"status": f"AMR {amr.serial_number} paused state: {amr.paused}", "paused": amr.paused})

    @action(detail=True, methods=["post"])
    def toggle_online(self, request, pk=None):
        amr = self.get_object()
        amr.is_online = not amr.is_online
        amr.save()
        return Response({"status": f"AMR {amr.serial_number} online state: {amr.is_online}", "is_online": amr.is_online})


class TopicControlViewSet(viewsets.ModelViewSet):
    """Cấu hình các MQTT topic ánh xạ cho từng xe."""
    queryset = TopicControl.objects.all()
    serializer_class = TopicControlSerializer


class AmrStateLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Tra cứu lịch sử trạng thái đo xa của robot (Audit Log)."""
    queryset = AmrStateLog.objects.all().order_by("-created_at")
    serializer_class = AmrStateLogSerializer
