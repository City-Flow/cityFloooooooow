# cityFlow/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, UserProfile, District, WeatherRecord,
    WaterConsumption, WaterPrediction,
    AirQuality, AirPrediction,
    TourismPressure, Tag, IncidentReport, Alert,
)


# ──────────────────────────────────────────────
# USERS + PROFILE
# ──────────────────────────────────────────────
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ("id", "email", "name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "name")
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Información personal", {"fields": ("name", "role")}),
        ("Permisos", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "role", "password1", "password2"),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone_number", "department", "created_at")
    search_fields = ("user__email", "user__name", "phone_number")


# ──────────────────────────────────────────────
# DISTRICT (maestro)
# ──────────────────────────────────────────────
@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "area_km2", "population", "latitude", "longitude")
    search_fields = ("code", "name")
    ordering = ("name",)


# ──────────────────────────────────────────────
# WEATHER
# ──────────────────────────────────────────────
@admin.register(WeatherRecord)
class WeatherRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "district", "date", "temp_avg_celsius", "temp_max_celsius",
                    "rainfall_mm", "humidity_percent")
    list_filter = ("date", "district")
    search_fields = ("district__code", "district__name")
    date_hierarchy = "date"


# ──────────────────────────────────────────────
# WATER — consumo + predicción
# ──────────────────────────────────────────────
@admin.register(WaterConsumption)
class WaterConsumptionAdmin(admin.ModelAdmin):
    list_display = ("id", "get_district_code", "get_district_name",
                    "consumption_m3", "domestic_consumption_m3",
                    "commercial_consumption_m3", "period_date")
    list_filter = ("period_date", "district")
    search_fields = ("district__code", "district__name")
    date_hierarchy = "period_date"

    @admin.display(description="Código distrito", ordering="district__code")
    def get_district_code(self, obj):
        return obj.district.code

    @admin.display(description="Distrito", ordering="district__name")
    def get_district_name(self, obj):
        return obj.district.name


@admin.register(WaterPrediction)
class WaterPredictionAdmin(admin.ModelAdmin):
    list_display = ("id", "district", "target_date",
                    "expected_consumption_m3", "observed_consumption_m3",
                    "deviation_pct", "anomaly_score", "is_anomaly",
                    "status", "model_version")
    list_filter = ("is_anomaly", "status", "target_date", "district")
    search_fields = ("district__code", "district__name", "model_version")
    date_hierarchy = "target_date"


# ──────────────────────────────────────────────
# AIR — calidad + predicción
# ──────────────────────────────────────────────
@admin.register(AirQuality)
class AirQualityAdmin(admin.ModelAdmin):
    list_display = ("id", "get_district_code", "get_district_name",
                    "no2_level", "pm10_level", "period_date")
    list_filter = ("period_date", "district")
    search_fields = ("district__code", "district__name")
    date_hierarchy = "period_date"

    @admin.display(description="Código distrito", ordering="district__code")
    def get_district_code(self, obj):
        return obj.district.code

    @admin.display(description="Distrito", ordering="district__name")
    def get_district_name(self, obj):
        return obj.district.name


@admin.register(AirPrediction)
class AirPredictionAdmin(admin.ModelAdmin):
    list_display = ("id", "district", "forecast_at",
                    "no2_predicted", "pm10_predicted", "model_version", "created_at")
    list_filter = ("forecast_at", "district", "model_version")
    search_fields = ("district__code", "district__name", "model_version")
    date_hierarchy = "forecast_at"


# ──────────────────────────────────────────────
# TOURISM PRESSURE
# ──────────────────────────────────────────────
@admin.register(TourismPressure)
class TourismPressureAdmin(admin.ModelAdmin):
    list_display = ("id", "get_district_code", "get_district_name",
                    "hut_count", "avg_noise_db", "period_date")
    list_filter = ("period_date", "district")
    search_fields = ("district__code", "district__name")
    date_hierarchy = "period_date"

    @admin.display(description="Código distrito", ordering="district__code")
    def get_district_code(self, obj):
        return obj.district.code

    @admin.display(description="Distrito", ordering="district__name")
    def get_district_name(self, obj):
        return obj.district.name


# ──────────────────────────────────────────────
# TAGS + INCIDENTS (N:M)
# ──────────────────────────────────────────────
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "district", "status", "created_at")
    list_filter = ("status", "district", "created_at")
    search_fields = ("title", "description", "user__email", "district__name")
    filter_horizontal = ("tags",)
    date_hierarchy = "created_at"


# ──────────────────────────────────────────────
# ALERTS (WebSockets)
# ──────────────────────────────────────────────
@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id", "alert_type", "severity", "title",
                    "district", "status", "created_at")
    list_filter = ("alert_type", "severity", "status", "district")
    search_fields = ("title", "message", "district__name")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)