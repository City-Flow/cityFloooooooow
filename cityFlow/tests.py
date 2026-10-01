from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from cityFlow.models import District, WaterConsumption

User = get_user_model()


class CityFlowAPITests(APITestCase):

    def setUp(self):
        # Base user and authenticated client setup
        self.user = User.objects.create_user(
            email="tester@cityflow.com",
            name="Tester",
            password="securepassword123",
            role="admin"
        )
        self.client.force_authenticate(user=self.user)

        # Base district
        self.district = District.objects.create(
            code="01",
            name="Ciutat Vella",
            area_km2=4.49,
            population=109672,
            latitude=41.380200,
            longitude=2.173200
        )

    # 1. User & Profile
    def test_user_creation_and_profile_signal(self):
        self.assertTrue(hasattr(self.user, "profile"))

    # 2. Districts Endpoints
    def test_get_districts_list(self):
        response = self.client.get("/api/districts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_district_success(self):
        payload = {
            "code": "02",
            "name": "Eixample",
            "area_km2": "7.46",
            "population": 266416,
            "latitude": "41.388800",
            "longitude": "2.164500"
        }
        response = self.client.post("/api/districts/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_district_invalid_data(self):
        # Missing required fields
        payload = {"name": "Incomplete District"}
        response = self.client.post("/api/districts/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 3. Water Consumption & Constraints
    def test_create_water_consumption_success(self):
        payload = {
            "district": self.district.id,
            "consumption_m3": "1250.50",
            "period_date": "2026-09-01"
        }
        response = self.client.post("/api/water-consumption/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_water_consumption_unique_constraint(self):
        WaterConsumption.objects.create(
            district=self.district,
            consumption_m3=1000.0,
            period_date="2026-09-01"
        )
        # Attempt duplicate entry for same district and period_date
        payload = {
            "district": self.district.id,
            "consumption_m3": "2000.00",
            "period_date": "2026-09-01"
        }
        response = self.client.post("/api/water-consumption/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)