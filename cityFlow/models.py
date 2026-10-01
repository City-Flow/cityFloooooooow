# cityFlow/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models.signals import post_save
from django.dispatch import receiver


# ══════════════════════════════════════════════
# 1. AUTENTICACIÓN
# ══════════════════════════════════════════════

class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        return self.create_user(email, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("admin", "Administrador"),
        ("analyst", "Analista"),
        ("viewer", "Visualizador"),
    ]

    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="viewer")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.name} <{self.email}>"


class UserProfile(models.Model):
    """1:1 con User. Se autocrea vía signal."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_profiles"

    def __str__(self):
        return f"Profile de {self.user.email}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


# ══════════════════════════════════════════════
# 2. MAESTRO: DISTRICT
# ══════════════════════════════════════════════

class District(models.Model):
    """Distrito maestro. Coordenadas para Folium."""
    code = models.CharField(max_length=10, unique=True, help_text="Matches GeoJSON")
    name = models.CharField(max_length=100)
    area_km2 = models.DecimalField(max_digits=6, decimal_places=2)
    population = models.IntegerField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Centroid for Folium")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Centroid for Folium")

    class Meta:
        db_table = "districts"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


# ══════════════════════════════════════════════
# 3. METEOROLOGÍA
# ══════════════════════════════════════════════

class WeatherRecord(models.Model):
    district = models.ForeignKey(District, on_delete=models.SET_NULL, related_name="weather_records", null=True, blank=True)
    date = models.DateField(db_index=True)
    temp_avg_celsius = models.DecimalField(max_digits=5, decimal_places=2)
    temp_max_celsius = models.DecimalField(max_digits=5, decimal_places=2)
    rainfall_mm = models.DecimalField(max_digits=6, decimal_places=2)
    humidity_percent = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = "weather_records"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["district", "date"], name="unique_weather_district_date")
        ]

    def __str__(self):
        return f"{self.district} - {self.date}"


# ══════════════════════════════════════════════
# 4. CONSUMO DE AGUA + PREDICCIÓN
# ══════════════════════════════════════════════

class WaterConsumption(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="water_consumptions", null=True, blank=True)
    consumption_m3 = models.DecimalField(max_digits=12, decimal_places=2)
    domestic_consumption_m3 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commercial_consumption_m3 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    period_date = models.DateField(db_index=True)

    class Meta:
        db_table = "water_consumption"
        ordering = ["-period_date"]
        constraints = [
            models.UniqueConstraint(fields=["district", "period_date"], name="unique_water_district_period")
        ]

    def __str__(self):
        return f"{self.district.code} - {self.period_date}: {self.consumption_m3} m³"


class WaterPrediction(models.Model):
    STATUS_CHOICES = [
        ("pending_review", "Pendiente de revisión"),
        ("verified_leak", "Fuga verificada"),
        ("false_positive", "Falso positivo"),
    ]

    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="water_predictions", null=True, blank=True)
    target_date = models.DateField(db_index=True)
    expected_consumption_m3 = models.DecimalField(max_digits=12, decimal_places=2)
    observed_consumption_m3 = models.DecimalField(max_digits=12, decimal_places=2)
    deviation_pct = models.FloatField(help_text="% diferencia observado vs esperado")
    anomaly_score = models.FloatField(help_text="0.0 a 1.0")
    is_anomaly = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending_review")
    model_version = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "water_predictions"
        ordering = ["-target_date"]
        constraints = [
            models.UniqueConstraint(fields=["district", "target_date"], name="unique_water_pred_district_date")
        ]

    def __str__(self):
        return f"{self.district.code} - {self.target_date} (anomaly={self.is_anomaly})"


# ══════════════════════════════════════════════
# 5. CALIDAD DEL AIRE + PREDICCIÓN
# ══════════════════════════════════════════════

class AirQuality(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="air_qualities", null=True, blank=True)
    no2_level = models.DecimalField(max_digits=6, decimal_places=2, help_text="µg/m³")
    pm10_level = models.DecimalField(max_digits=6, decimal_places=2, help_text="µg/m³")
    period_date = models.DateField(db_index=True)

    class Meta:
        db_table = "air_quality"
        ordering = ["-period_date"]
        constraints = [
            models.UniqueConstraint(fields=["district", "period_date"], name="unique_air_district_period")
        ]

    def __str__(self):
        return f"{self.district.code} - {self.period_date}"


class AirPrediction(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="air_predictions")
    forecast_at = models.DateTimeField(db_index=True)
    no2_predicted = models.DecimalField(max_digits=6, decimal_places=2)
    pm10_predicted = models.DecimalField(max_digits=6, decimal_places=2)
    model_version = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "air_predictions"
        ordering = ["-forecast_at"]

    def __str__(self):
        return f"{self.district.code} @ {self.forecast_at}"


# ══════════════════════════════════════════════
# 6. PRESIÓN TURÍSTICA
# ══════════════════════════════════════════════

class TourismPressure(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="tourism_pressures")
    hut_count = models.IntegerField(help_text="Viviendas de uso turístico (HUT)")
    avg_noise_db = models.DecimalField(max_digits=5, decimal_places=2, help_text="dB")
    period_date = models.DateField(db_index=True)

    class Meta:
        db_table = "tourism_pressure"
        ordering = ["-period_date"]
        constraints = [
            models.UniqueConstraint(fields=["district", "period_date"], name="unique_tourism_district_period")
        ]

    def __str__(self):
        return f"{self.district.code} - {self.period_date}"


# ══════════════════════════════════════════════
# 7. INCIDENCIAS + TAGS (N:M)
# ══════════════════════════════════════════════

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        db_table = "tags"
        ordering = ["name"]

    def __str__(self):
        return self.name


class IncidentReport(models.Model):
    STATUS_CHOICES = [
        ("open", "Abierta"),
        ("in_progress", "En progreso"),
        ("resolved", "Resuelta"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="incidents")
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="incidents")
    title = models.CharField(max_length=150)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    tags = models.ManyToManyField(Tag, related_name="incidents", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "incident_reports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.id} {self.title} ({self.status})"


# ══════════════════════════════════════════════
# 8. ALERTAS (para WebSockets)
# ══════════════════════════════════════════════

class Alert(models.Model):
    ALERT_TYPE_CHOICES = [
        ("water_anomaly", "Anomalía de agua"),
        ("air_quality", "Calidad del aire"),
        ("incident", "Incidencia"),
    ]
    SEVERITY_CHOICES = [
        ("critical", "Crítica"),
        ("warning", "Advertencia"),
        ("info", "Informativa"),
    ]
    STATUS_CHOICES = [
        ("unread", "No leída"),
        ("acknowledged", "Reconocida"),
        ("resolved", "Resuelta"),
    ]

    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="alerts")
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    title = models.CharField(max_length=150)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unread")
    related_object_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alerts"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["district", "alert_type", "severity", "title"], name="unique_alert")
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title}"