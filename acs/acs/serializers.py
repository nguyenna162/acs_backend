from rest_framework import serializers
from .models import Order, OrderMaster, SubOrder, SupplyRequest, ActionDispatch, Log


class SubOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubOrder
        fields = "__all__"


class OrderMasterSerializer(serializers.ModelSerializer):
    suborders = SubOrderSerializer(many=True, read_only=True)

    class Meta:
        model = OrderMaster
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    suborders = SubOrderSerializer(many=True, read_only=True)
    source_node_name = serializers.CharField(source="source_node.name", read_only=True)
    target_node_name = serializers.CharField(source="target_node.name", read_only=True)

    class Meta:
        model = Order
        fields = "__all__"
        extra_kwargs = {
            "order_id": {"required": False},
        }

    def create(self, validated_data):
        if not validated_data.get("order_id"):
            import time
            validated_data["order_id"] = f"ORD_{int(time.time()*1000)}"
        return super().create(validated_data)


class SupplyRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplyRequest
        fields = "__all__"


class ActionDispatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionDispatch
        fields = "__all__"


class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = "__all__"


class FindPathInputSerializer(serializers.Serializer):
    start_node_id = serializers.CharField(required=True, help_text="ID của Node xuất phát")
    target_node_id = serializers.CharField(required=True, help_text="ID của Node đích")


class DispatchAMRInputSerializer(serializers.Serializer):
    amr_serial = serializers.CharField(required=False, allow_blank=True, help_text="Mã serial AMR chỉ định (để trống nếu muốn hệ thống tự lập lịch)")
    source_node_id = serializers.CharField(required=False, allow_blank=True, help_text="Điểm lấy hàng / xuất phát")
    target_node_id = serializers.CharField(required=True, help_text="Điểm trả hàng / đích đến")
    order_type = serializers.ChoiceField(choices=Order.Type.choices, default=Order.Type.TRANSPORT)
    priority = serializers.ChoiceField(choices=Order.Priority.choices, default=Order.Priority.NORMAL)
    description = serializers.CharField(required=False, allow_blank=True, default="")
