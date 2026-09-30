from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

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

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True")

        return self.create_user(email, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = [
        ("admin", "Administrador"),
        ("analyst", "Analista"),
        ("viewer", "Visualizador"),
    ]

    name = models.CharField(max_length=120)
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255, db_column="password_hash")
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default="viewer")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.name} <{self.email}>"


class WaterConsumption(models.Model):
    district_code = models.CharField(max_length=10)
    district_name = models.CharField(max_length=100)
    consumption_m3 = models.DecimalField(max_digits=10, decimal_places=2)
    period_date = models.DateField()

    class Meta:
        db_table = "water_consumption"
        verbose_name = "Consumo de agua"
        verbose_name_plural = "Consumos de agua"
        ordering = ["-period_date"]
        indexes = [models.Index(fields=["district_code", "period_date"])]

    def __str__(self):
        return f"{self.district_name} - {self.period_date} ({self.consumption_m3} m³)"



class AirQuality(models.Model):
    district_code = models.CharField(max_length=10)
    district_name = models.CharField(max_length=100)
    no2_level = models.DecimalField(max_digits=6, decimal_places=2, help_text="µg/m³")
    pm10_level = models.DecimalField(max_digits=6, decimal_places=2, help_text="µg/m³")
    period_date = models.DateField()

    class Meta:
        db_table = "air_quality"
        verbose_name = "Calidad del aire"
        verbose_name_plural = "Calidad del aire"
        ordering = ["-period_date"]
        indexes = [models.Index(fields=["district_code", "period_date"])]

    def __str__(self):
        return f"{self.district_name} - {self.period_date} (NO₂: {self.no2_level}, PM10: {self.pm10_level})"



class TourismPressure(models.Model):
    district_code = models.CharField(max_length=10)
    district_name = models.CharField(max_length=100)
    hut_count = models.IntegerField(help_text="Número de viviendas de uso turístico (HUT)")
    avg_noise_db = models.DecimalField(max_digits=5, decimal_places=2, help_text="Nivel acústico en dB")
    period_date = models.DateField()

    class Meta:
        db_table = "tourism_pressure"
        verbose_name = "Presión turística"
        verbose_name_plural = "Presión turística"
        ordering = ["-period_date"]
        indexes = [models.Index(fields=["district_code", "period_date"])]

    def __str__(self):
        return f"{self.district_name} - {self.period_date} ({self.hut_count} HUT, {self.avg_noise_db} dB)"