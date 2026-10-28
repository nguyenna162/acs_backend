import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "acs.settings")
django.setup()

from map.models import MapBase, ZoneSet, TrafficZone, Node, Edge, Action
from amr.models import AmrVehicle, TopicControl
from buffer.models import Buffer
from acs.models import Order, SupplyRequest
from django.utils import timezone


def seed_data():
    print("[Seed] Initializing CNC Prod 2G Factory Data...")

    # 1. Create Base Map
    map_base, _ = MapBase.objects.get_or_create(
        name="CNC_Prod_2G_Main_Floor",
        defaults={
            "part": "CNC_2G",
            "version": "1.0.0",
            "status": MapBase.Status.ACTIVE,
            "description": "Bản đồ phân xưởng sản xuất CNC Prod 2G",
        },
    )

    # 2. Create ZoneSet and TrafficZone
    zone_set, _ = ZoneSet.objects.get_or_create(
        map=map_base,
        name="ZoneSet_Standard_2G",
        defaults={"version": "1.0", "is_active": True},
    )

    tz_aisle, _ = TrafficZone.objects.get_or_create(
        zone_set=zone_set,
        map=map_base,
        name="Aisle_Central",
        defaults={"type": TrafficZone.ZoneType.AISLE, "max_occupancy": 3, "max_speed": 1.5},
    )

    tz_charge, _ = TrafficZone.objects.get_or_create(
        zone_set=zone_set,
        map=map_base,
        name="Zone_Charging_Bay",
        defaults={"type": TrafficZone.ZoneType.CHARGING_AREA, "max_occupancy": 2, "max_speed": 0.8},
    )

    # 3. Create Nodes
    node_configs = [
        ("N01_Transit_Central", Node.NodeTypeChoice.TRANSIT, 10.0, 30.0, 0.0, tz_aisle),
        ("N02_Transit_East", Node.NodeTypeChoice.TRANSIT, 30.0, 30.0, 0.0, tz_aisle),
        ("N03_Transit_West", Node.NodeTypeChoice.TRANSIT, 50.0, 30.0, 0.0, tz_aisle),
        ("N04_Pick_CNC1", Node.NodeTypeChoice.PICK, 30.0, 15.0, 1.57, tz_aisle),
        ("N05_Drop_CNC1", Node.NodeTypeChoice.DROP, 30.0, 45.0, -1.57, tz_aisle),
        ("N06_Pick_CNC2", Node.NodeTypeChoice.PICK, 50.0, 15.0, 1.57, tz_aisle),
        ("N07_Drop_CNC2", Node.NodeTypeChoice.DROP, 50.0, 45.0, -1.57, tz_aisle),
        ("N08_Charge_Station", Node.NodeTypeChoice.CHARGE, 10.0, 10.0, 3.14, tz_charge),
        ("N09_Buffer_Raw", Node.NodeTypeChoice.PICK, 70.0, 30.0, 0.0, tz_aisle),
        ("N10_Buffer_Finish", Node.NodeTypeChoice.DROP, 85.0, 30.0, 0.0, tz_aisle),
    ]

    nodes_dict = {}
    for name, n_type, x, y, theta, zone in node_configs:
        node, _ = Node.objects.get_or_create(
            map=map_base,
            name=name,
            defaults={
                "type": n_type,
                "x": x,
                "y": y,
                "theta": theta,
                "traffic_zone": zone,
                "use_node": True,
            },
        )
        nodes_dict[name] = node

    # 4. Create Edges
    edge_pairs = [
        ("N01_Transit_Central", "N02_Transit_East", 20.0),
        ("N02_Transit_East", "N03_Transit_West", 20.0),
        ("N02_Transit_East", "N04_Pick_CNC1", 15.0),
        ("N02_Transit_East", "N05_Drop_CNC1", 15.0),
        ("N03_Transit_West", "N06_Pick_CNC2", 15.0),
        ("N03_Transit_West", "N07_Drop_CNC2", 15.0),
        ("N01_Transit_Central", "N08_Charge_Station", 22.3),
        ("N03_Transit_West", "N09_Buffer_Raw", 20.0),
        ("N09_Buffer_Raw", "N10_Buffer_Finish", 15.0),
    ]

    for start_name, end_name, length in edge_pairs:
        u = nodes_dict[start_name]
        v = nodes_dict[end_name]
        Edge.objects.get_or_create(
            map=map_base,
            start_node=u,
            end_node=v,
            defaults={
                "length": length,
                "max_speed": 1.2,
                "direction": Edge.DirectionChoice.BIDIRECTIONAL,
                "name": f"E_{start_name}_{end_name}",
            },
        )

    # 5. Create Buffers
    b1, _ = Buffer.objects.get_or_create(
        rssid="RFID_BUF_CNC_01",
        defaults={
            "name": "Buffer_CNC_Line1_In",
            "type": Buffer.BufferType.PICK,
            "product_model": "SM-S928_FRAME",
            "node": nodes_dict["N04_Pick_CNC1"],
            "status": Buffer.Status.OCCUPIED,
        },
    )

    b2, _ = Buffer.objects.get_or_create(
        rssid="RFID_BUF_CNC_02",
        defaults={
            "name": "Buffer_CNC_Line1_Out",
            "type": Buffer.BufferType.DROP,
            "product_model": "SM-S928_FRAME",
            "node": nodes_dict["N05_Drop_CNC1"],
            "status": Buffer.Status.EMPTY,
        },
    )

    # 6. Create AMRs
    amr_list = [
        ("AMR_001", "AMR_LIFT_500", "SEVT", 10.0, 30.0, "N01_Transit_Central", True, True, 92.5),
        ("AMR_002", "AMR_LIFT_500", "SEVT", 85.0, 30.0, "N10_Buffer_Finish", True, True, 88.0),
        ("AMR_003", "AMR_TOW_1000", "SEVT", 10.0, 10.0, "N08_Charge_Station", True, False, 45.0),
    ]

    for serial, model, mfg, x, y, last_node, online, idle, battery in amr_list:
        amr, _ = AmrVehicle.objects.get_or_create(
            serial_number=serial,
            defaults={
                "amr_model": model,
                "manufacturer": mfg,
                "version": "2.1.0",
                "is_online": online,
                "is_idle": idle,
                "last_node_id": str(nodes_dict[last_node].id),
                "last_heartbeat": timezone.now(),
                "amr_position": {"x": x, "y": y, "theta": 0.0, "mapId": str(map_base.id)},
                "battery_state": {"batteryCharge": battery, "charging": serial == "AMR_003"},
                "operating_mode": AmrVehicle.OperatingMode.AUTOMATIC,
            },
        )

        # Setup TopicControl
        for t_type in [TopicControl.TopicType.ORDER, TopicControl.TopicType.STATE, TopicControl.TopicType.INSTANT_ACTIONS, TopicControl.TopicType.CONNECTION]:
            topic_str = f"uagv/v2/{mfg}/{serial}/{t_type}"
            TopicControl.objects.get_or_create(
                topic=topic_str,
                defaults={
                    "topic_type": t_type,
                    "amr": amr,
                    "manufacturer": mfg,
                    "version": "2.1.0",
                    "header_id": 1,
                    "last_call": timezone.now(),
                },
            )

    # 7. Create Sample Supply Request
    SupplyRequest.objects.get_or_create(
        line_id="CNC_2G_L1",
        buffer=b1,
        material_id="MAT_ALUMINUM_BLOCK_7075",
        defaults={
            "priority": 8,
            "sla_deadline": timezone.now() + timezone.timedelta(minutes=15),
            "status": SupplyRequest.Status.PENDING,
        },
    )

    print("[Seed] Successfully seeded factory nodes, edges, buffers, AMRs, and MQTT topics!")


if __name__ == "__main__":
    seed_data()
