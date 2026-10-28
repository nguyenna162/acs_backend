from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from .views import (
    OrderViewSet,
    OrderMasterViewSet,
    SubOrderViewSet,
    SupplyRequestViewSet,
    LogViewSet,
    find_path_vda,
    dispatch_amr,
    system_logs_file,
    robot_telemetry_stream,
)

router = DefaultRouter()
router.register(r"orders", OrderViewSet)
router.register(r"masters", OrderMasterViewSet)
router.register(r"suborders", SubOrderViewSet)
router.register(r"supply-requests", SupplyRequestViewSet)
router.register(r"logs", LogViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Web Dashboard & Management views
    path("", TemplateView.as_view(template_name="dashboard.html"), name="dashboard"),
    path("orders/", TemplateView.as_view(template_name="orders.html"), name="orders"),
    path("robots/", TemplateView.as_view(template_name="robots.html"), name="robots"),
    path("maps/", TemplateView.as_view(template_name="maps.html"), name="maps"),
    # Real-time WebSocket / HTTP telemetry endpoint for Clients
    path("ws/robot/telemetry/", robot_telemetry_stream, name="ws_robot_telemetry"),
    path("ws/robot/telemetry", robot_telemetry_stream),
    path("api/acs/telemetry/", robot_telemetry_stream, name="api_robot_telemetry"),
    # OpenAPI & Swagger Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Core ACS endpoints
    path("api/acs/", include(router.urls)),
    path("api/acs/find-path/", find_path_vda, name="find_path_vda"),
    path("api/acs/dispatch/", dispatch_amr, name="dispatch_amr"),
    path("api/acs/log-file/", system_logs_file, name="system_logs_file"),
    # Domain Subsystem endpoints
    path("api/amr/", include("amr.urls")),
    path("api/buffer/", include("buffer.urls")),
    path("api/map/", include("map.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
