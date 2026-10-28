from rest_framework import serializers
from .models import AmrVehicle, TopicControl, AmrStateLog


class TopicControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicControl
        fields = "__all__"


class AmrStateLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmrStateLog
        fields = "__all__"


class AmrVehicleSerializer(serializers.ModelSerializer):
    topics = TopicControlSerializer(many=True, read_only=True)

    class Meta:
        model = AmrVehicle
        fields = "__all__"
