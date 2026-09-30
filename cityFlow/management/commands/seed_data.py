# cityFlow/management/commands/seed_data.py
"""
Comando: python manage.py seed_data
Genera datos de prueba: distritos + 120 días de aire, clima y agua,
con una anomalía de consumo inyectada el día 100.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from cityFlow.models import District, AirQuality, WaterConsumption, WeatherRecord


DISTRICTS = [
    {"code": "CENTRO",     "name": "Centro",     "area_km2": "5.20",  "population": 130000,
     "latitude": "40.416800", "longitude": "-3.703800"},
    {"code": "SALAMANCA",  "name": "Salamanca",  "area_km2": "6.10",  "population": 145000,
     "latitude": "40.430000", "longitude": "-3.680000"},
    {"code": "CHAMBERI",   "name": "Chamberí",   "area_km2": "4.70",  "population": 138000,
     "latitude": "40.435000", "longitude": "-3.700000"},
]


class Command(BaseCommand):
    help = "Rellena la BD con datos de prueba para CityFlow."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=120,
                            help="Días de historial a generar (default: 120)")
        parser.add_argument("--fresh", action="store_true",
                            help="Borra los datos previos de cada distrito antes de sembrar.")

    def handle(self, *args, **options):
        days = options["days"]
        fresh = options["fresh"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Sembrando {len(DISTRICTS)} distritos × {days} días…"
        ))

        for info in DISTRICTS:
            district, _ = District.objects.get_or_create(
                code=info["code"],
                defaults=dict(
                    name=info["name"],
                    area_km2=Decimal(info["area_km2"]),
                    population=info["population"],
                    latitude=Decimal(info["latitude"]),
                    longitude=Decimal(info["longitude"]),
                ),
            )

            if fresh:
                AirQuality.objects.filter(district=district).delete()
                WeatherRecord.objects.filter(district=district).delete()
                WaterConsumption.objects.filter(district=district).delete()

            created_air = created_w = created_water = 0
            start = date.today() - timedelta(days=days)

            # Distritos con más base de consumo
            base_consumption = 1000 + (info["population"] / 1000)

            for i in range(days):
                day = start + timedelta(days=i)

                _, c1 = AirQuality.objects.get_or_create(
                    district=district,
                    period_date=day,
                    defaults=dict(
                        no2_level=Decimal(str(round(30 + 15 * random.random(), 2))),
                        pm10_level=Decimal(str(round(20 + 10 * random.random(), 2))),
                    ),
                )
                created_air += int(c1)

                _, c2 = WeatherRecord.objects.get_or_create(
                    district=district,
                    date=day,
                    defaults=dict(
                        temp_avg_celsius=Decimal(str(round(18 + 8 * random.random(), 2))),
                        temp_max_celsius=Decimal(str(round(25 + 8 * random.random(), 2))),
                        rainfall_mm=Decimal(str(round(random.random() * 5, 2))),
                        humidity_percent=Decimal(str(round(50 + 20 * random.random(), 2))),
                    ),
                )
                created_w += int(c2)

                # Consumo base + ruido
                consumption = base_consumption + 100 * random.random()

                # Inyectamos anomalías: día 100 en CENTRO, día 80 en SALAMANCA
                if (info["code"] == "CENTRO" and i == 100) or \
                   (info["code"] == "SALAMANCA" and i == 80):
                    consumption *= 1.6

                _, c3 = WaterConsumption.objects.get_or_create(
                    district=district,
                    period_date=day,
                    defaults=dict(
                        consumption_m3=Decimal(str(round(consumption, 2))),
                        domestic_consumption_m3=Decimal(str(round(consumption * 0.6, 2))),
                        commercial_consumption_m3=Decimal(str(round(consumption * 0.4, 2))),
                    ),
                )
                created_water += int(c3)

            self.stdout.write(self.style.SUCCESS(
                f"  ✓ {district.code:12} | "
                f"aire: {created_air:3} | clima: {created_w:3} | agua: {created_water:3}"
            ))

        self.stdout.write(self.style.SUCCESS("\nSeed completado."))
        self.stdout.write(f"  Distritos:          {District.objects.count()}")
        self.stdout.write(f"  AirQuality:         {AirQuality.objects.count()}")
        self.stdout.write(f"  WeatherRecord:      {WeatherRecord.objects.count()}")
        self.stdout.write(f"  WaterConsumption:   {WaterConsumption.objects.count()}")