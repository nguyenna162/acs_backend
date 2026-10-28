from rest_framework.routers import DefaultRouter
from .views import (
    MapBaseViewSet,
    WorldMapLayerViewSet,
    GridMapLayerViewSet,
    ZoneSetViewSet,
    TrafficZoneViewSet,
    NodeViewSet,
    EdgeViewSet,
    ActionViewSet,
)

router = DefaultRouter()
router.register(r"bases", MapBaseViewSet)
router.register(r"world-layers", WorldMapLayerViewSet)
router.register(r"grid-layers", GridMapLayerViewSet)
router.register(r"zone-sets", ZoneSetViewSet)
router.register(r"traffic-zones", TrafficZoneViewSet)
router.register(r"nodes", NodeViewSet)
router.register(r"edges", EdgeViewSet)
router.register(r"actions", ActionViewSet)

urlpatterns = router.urls
