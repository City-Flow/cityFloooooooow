from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import *


router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"profiles", UserProfileViewSet)
router.register(r"districts", DistrictViewSet)
router.register(r"weather", WeatherRecordViewSet)
router.register(r"water-consumption", WaterConsumptionViewSet)
router.register(r"water-predictions", WaterPredictionViewSet)
router.register(r"air-quality", AirQualityViewSet)
router.register(r"air-predictions", AirPredictionViewSet)
router.register(r"tourism-pressure", TourismPressureViewSet)
router.register(r"tags", TagViewSet)
router.register(r"incidents", IncidentReportViewSet)
router.register(r"alerts", AlertViewSet)
router.register(r"predictions", PredictionViewSet, basename="predictions")


urlpatterns = [
    path("api/", include(router.urls)),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]