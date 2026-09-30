from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    User, UserProfile, District, WeatherRecord,
    WaterConsumption, WaterPrediction,
    AirQuality, AirPrediction,
    TourismPressure, Tag, IncidentReport, Alert,
)
from .serializers import *
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as http_status

from .models import District
from .serializers import (
    AirPredictionRequestSerializer,
    AirPredictionSerializer,
    WaterAnomalyRequestSerializer,
    WaterPredictionSerializer,
)
from .services.air_prediction import predict_air_quality, train_all_districts
from .services.water_anomalies import analyze_district, analyze_all_districts


class PredictionViewSet(viewsets.ViewSet):
    """
    Endpoints de predicción y análisis.

    GET  /api/predictions/air-quality/?district=3&hours=24
    POST /api/predictions/air-quality/train/
    GET  /api/anomalies/water/?district=3
    POST /api/anomalies/water/scan/
    """

    @action(detail=False, methods=["get"], url_path="air-quality")
    def air_quality(self, request):
        ser = AirPredictionRequestSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)

        try:
            district = District.objects.get(pk=ser.validated_data["district"])
        except District.DoesNotExist:
            return Response({"detail": "District no existe"}, status=404)

        preds = predict_air_quality(district, hours=ser.validated_data["hours"])
        return Response({
            "district_id": district.id,
            "district_code": district.code,
            "hours": ser.validated_data["hours"],
            "predictions": AirPredictionSerializer(preds, many=True).data,
        })

    @action(detail=False, methods=["post"], url_path="air-quality/train")
    def air_quality_train(self, request):
        results = train_all_districts()
        return Response([
            {
                "district_code": r.district_code,
                "n_samples": r.n_samples,
                "mae_no2_model": round(r.mae_no2_model, 3),
                "mae_no2_baseline": round(r.mae_no2_baseline, 3),
                "mae_pm10_model": round(r.mae_pm10_model, 3),
                "mae_pm10_baseline": round(r.mae_pm10_baseline, 3),
                "adopted": r.adopted,
            } for r in results
        ])

    @action(detail=False, methods=["get"], url_path="water-anomalies")
    def water_anomalies(self, request):
        ser = WaterAnomalyRequestSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        try:
            district = District.objects.get(pk=ser.validated_data["district"])
        except District.DoesNotExist:
            return Response({"detail": "District no existe"}, status=404)

        result = analyze_district(district, lookback_days=ser.validated_data["lookback_days"])
        preds = WaterPrediction.objects.filter(district=district, is_anomaly=True)
        return Response({
            "district_id": district.id,
            "district_code": district.code,
            "total_readings": result.total_readings,
            "anomalies_detected": result.anomalies_detected,
            "anomalies": WaterPredictionSerializer(preds, many=True).data,
        })

    @action(detail=False, methods=["post"], url_path="water-anomalies/scan")
    def water_anomalies_scan(self, request):
        results = analyze_all_districts()
        return Response([
            {
                "district_code": r.district_code,
                "total_readings": r.total_readings,
                "anomalies_detected": r.anomalies_detected,
                "predictions_created": r.predictions_created,
            } for r in results
        ])


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    def get_serializer_class(self):
        return UserCreateSerializer if self.action == "create" else UserSerializer


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class DistrictViewSet(viewsets.ModelViewSet):
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["code", "name"]


class WeatherRecordViewSet(viewsets.ModelViewSet):
    queryset = WeatherRecord.objects.all()
    serializer_class = WeatherRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["district", "date"]
    ordering_fields = ["date"]


class WaterConsumptionViewSet(viewsets.ModelViewSet):
    queryset = WaterConsumption.objects.select_related("district").all()
    serializer_class = WaterConsumptionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["district", "period_date"]
    ordering_fields = ["period_date"]


class WaterPredictionViewSet(viewsets.ModelViewSet):
    queryset = WaterPrediction.objects.select_related("district").all()
    serializer_class = WaterPredictionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["district", "is_anomaly", "status"]


class AirQualityViewSet(viewsets.ModelViewSet):
    queryset = AirQuality.objects.select_related("district").all()
    serializer_class = AirQualitySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["district", "period_date"]


class AirPredictionViewSet(viewsets.ModelViewSet):
    queryset = AirPrediction.objects.select_related("district").all()
    serializer_class = AirPredictionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["district"]


class TourismPressureViewSet(viewsets.ModelViewSet):
    queryset = TourismPressure.objects.select_related("district").all()
    serializer_class = TourismPressureSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["district", "period_date"]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IncidentReportViewSet(viewsets.ModelViewSet):
    queryset = IncidentReport.objects.select_related("user", "district").prefetch_related("tags")
    serializer_class = IncidentReportSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["district", "status", "user"]
    search_fields = ["title", "description"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.select_related("district").all()
    serializer_class = AlertSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["district", "alert_type", "severity", "status"]
    ordering_fields = ["created_at"]