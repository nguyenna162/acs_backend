from rest_framework.routers import DefaultRouter
from .views import AmrVehicleViewSet, TopicControlViewSet, AmrStateLogViewSet

router = DefaultRouter()
router.register(r"vehicles", AmrVehicleViewSet)
router.register(r"topics", TopicControlViewSet)
router.register(r"statelogs", AmrStateLogViewSet)

urlpatterns = router.urls
