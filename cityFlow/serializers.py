from rest_framework import serializers
from .models import (
    User, UserProfile, District, WeatherRecord,
    WaterConsumption, WaterPrediction,
    AirQuality, AirPrediction,
    TourismPressure, Tag, IncidentReport, Alert,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "is_active", "created_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "name", "password", "role"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = "__all__"


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = "__all__"


class WeatherRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherRecord
        fields = "__all__"


class WaterConsumptionSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)
    class Meta:
        model = WaterConsumption
        fields = "__all__"


class WaterPredictionSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)
    class Meta:
        model = WaterPrediction
        fields = "__all__"


class AirQualitySerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)
    class Meta:
        model = AirQuality
        fields = "__all__"


class AirPredictionSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)
    class Meta:
        model = AirPrediction
        fields = "__all__"


class TourismPressureSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)
    class Meta:
        model = TourismPressure
        fields = "__all__"


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class IncidentReportSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=Tag.objects.all(), source="tags"
    )
    user_name = serializers.CharField(source="user.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = IncidentReport
        fields = [
            "id", "user", "user_name", "district", "district_name",
            "title", "description", "status", "tags", "tag_ids",
            "created_at", "updated_at",
        ]
        read_only_fields = ["user", "created_at", "updated_at"]


class AlertSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)
    class Meta:
        model = Alert
        fields = "__all__"

# ─── Serializers de predicción (request/response custom) ───
class AirPredictionRequestSerializer(serializers.Serializer):
    district = serializers.IntegerField()
    hours = serializers.IntegerField(min_value=1, max_value=168, default=24)


class WaterAnomalyRequestSerializer(serializers.Serializer):
    district = serializers.IntegerField()
    lookback_days = serializers.IntegerField(min_value=7, max_value=365, default=90)