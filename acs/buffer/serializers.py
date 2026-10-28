from rest_framework import serializers
from .models import Buffer, Schedule, ScheduleStop, StopAction


class StopActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StopAction
        fields = "__all__"


class ScheduleStopSerializer(serializers.ModelSerializer):
    actions = StopActionSerializer(many=True, read_only=True)

    class Meta:
        model = ScheduleStop
        fields = "__all__"


class ScheduleSerializer(serializers.ModelSerializer):
    stops = ScheduleStopSerializer(many=True, read_only=True)

    class Meta:
        model = Schedule
        fields = "__all__"


class BufferSerializer(serializers.ModelSerializer):
    node_name = serializers.CharField(source="node.name", read_only=True)

    class Meta:
        model = Buffer
        fields = "__all__"
