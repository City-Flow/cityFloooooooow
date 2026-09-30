from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, WaterConsumption, AirQuality, TourismPressure


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "name", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("name", "email")
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Información personal", {"fields": ("name", "role")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "role", "password1", "password2"),
        }),
    )


@admin.register(WaterConsumption)
class WaterConsumptionAdmin(admin.ModelAdmin):
    list_display = ("id", "district_code", "district_name", "consumption_m3", "period_date")
    list_filter = ("period_date", "district_name")
    search_fields = ("district_code", "district_name")


@admin.register(AirQuality)
class AirQualityAdmin(admin.ModelAdmin):
    list_display = ("id", "district_code", "district_name", "no2_level", "pm10_level", "period_date")
    list_filter = ("period_date", "district_name")
    search_fields = ("district_code", "district_name")


@admin.register(TourismPressure)
class TourismPressureAdmin(admin.ModelAdmin):
    list_display = ("id", "district_code", "district_name", "hut_count", "avg_noise_db", "period_date")
    list_filter = ("period_date", "district_name")
    search_fields = ("district_code", "district_name")