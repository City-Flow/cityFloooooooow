from rest_framework import serializers
from .models import User, WaterConsumption, AirQuality, TourismPressure


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "role", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "name", "email", "password", "role"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class WaterConsumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterConsumption
        fields = "__all__"


class AirQualitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AirQuality
        fields = "__all__"


class TourismPressureSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourismPressure
        fields = "__all__"