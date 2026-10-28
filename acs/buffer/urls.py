from rest_framework.routers import DefaultRouter
from .views import BufferViewSet, ScheduleViewSet, ScheduleStopViewSet, StopActionViewSet

router = DefaultRouter()
router.register(r"stations", BufferViewSet)
router.register(r"schedules", ScheduleViewSet)
router.register(r"stops", ScheduleStopViewSet)
router.register(r"stop-actions", StopActionViewSet)

urlpatterns = router.urls
