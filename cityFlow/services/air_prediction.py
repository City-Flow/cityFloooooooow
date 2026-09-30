# cityFlow/services/air_prediction.py
"""
Servicio de predicción de calidad del aire (NO2, PM10).

Estrategia:
  1. Baseline: repetir el último valor observado.
  2. Modelo: RandomForestRegressor por contaminante.
  3. Solo se adopta el modelo si mejora al baseline en validación temporal.

Entrada: AirQuality + WeatherRecord por distrito.
Salida: AirPrediction (no2_predicted, pm10_predicted).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from django.db.models import QuerySet
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from cityFlow.models import AirQuality, AirPrediction, District, WeatherRecord

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

MODEL_VERSION = "air-v1"


# ──────────────────────────────────────────────
# 1. Construcción del dataset
# ──────────────────────────────────────────────
def _build_dataframe(district: District) -> pd.DataFrame:
    """Une AirQuality + WeatherRecord por fecha para un distrito."""

    air_qs: QuerySet = AirQuality.objects.filter(district=district).order_by("period_date")
    weather_qs: QuerySet = WeatherRecord.objects.filter(district=district).order_by("date")

    air_df = pd.DataFrame(list(air_qs.values("period_date", "no2_level", "pm10_level")))
    air_df["no2_level"] = air_df["no2_level"].astype(float)
    air_df["pm10_level"] = air_df["pm10_level"].astype(float)
    weather_df = pd.DataFrame(list(weather_qs.values(
        "date", "temp_avg_celsius", "temp_max_celsius", "rainfall_mm", "humidity_percent"
    )))
    weather_df["temp_avg_celsius"] = weather_df["temp_avg_celsius"].astype(float)
    weather_df["temp_max_celsius"] = weather_df["temp_max_celsius"].astype(float)
    weather_df["rainfall_mm"] = weather_df["rainfall_mm"].astype(float)
    weather_df["humidity_percent"] = weather_df["humidity_percent"].astype(float)

    if air_df.empty:
        return pd.DataFrame()

    air_df = air_df.rename(columns={"period_date": "date"})
    air_df["date"] = pd.to_datetime(air_df["date"])

    if not weather_df.empty:
        weather_df["date"] = pd.to_datetime(weather_df["date"])
        df = air_df.merge(weather_df, on="date", how="left")
    else:
        df = air_df
        for col in ("temp_avg_celsius", "temp_max_celsius", "rainfall_mm", "humidity_percent"):
            df[col] = np.nan

    # Features temporales
    df = df.sort_values("date").reset_index(drop=True)
    df["dow"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear

    # Lags (valores anteriores del propio contaminante)
    for lag in (1, 2, 3, 7):
        df[f"no2_lag{lag}"] = df["no2_level"].shift(lag)
        df[f"pm10_lag{lag}"] = df["pm10_level"].shift(lag)

    return df.dropna().reset_index(drop=True)


FEATURE_COLS = [
    "temp_avg_celsius", "temp_max_celsius", "rainfall_mm", "humidity_percent",
    "dow", "month", "day_of_year",
    "no2_lag1", "no2_lag2", "no2_lag3", "no2_lag7",
    "pm10_lag1", "pm10_lag2", "pm10_lag3", "pm10_lag7",
]


# ──────────────────────────────────────────────
# 2. Entrenamiento
# ──────────────────────────────────────────────
@dataclass
class TrainResult:
    district_code: str
    n_samples: int
    mae_no2_model: float
    mae_no2_baseline: float
    mae_pm10_model: float
    mae_pm10_baseline: float
    adopted: bool


def train_district_model(district: District) -> TrainResult | None:
    """Entrena RandomForest para un distrito. Guarda el modelo si mejora al baseline."""

    df = _build_dataframe(district)
    if len(df) < 30:
        logger.warning("District %s: muy pocos datos (%d). Skip.", district.code, len(df))
        return None

    # Split temporal 80/20 (sin shuffle!)
    split = int(len(df) * 0.8)
    train, test = df.iloc[:split], df.iloc[split:]

    X_train, X_test = train[FEATURE_COLS], test[FEATURE_COLS]
    y_no2_train, y_no2_test = train["no2_level"], test["no2_level"]
    y_pm10_train, y_pm10_test = train["pm10_level"], test["pm10_level"]

    # Modelo
    rf_no2 = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    rf_pm10 = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    rf_no2.fit(X_train, y_no2_train)
    rf_pm10.fit(X_train, y_pm10_train)

    # Baseline: repetir el último valor (lag1)
    baseline_no2 = test["no2_lag1"].values
    baseline_pm10 = test["pm10_lag1"].values

    mae_no2_model = mean_absolute_error(y_no2_test, rf_no2.predict(X_test))
    mae_no2_baseline = mean_absolute_error(y_no2_test, baseline_no2)
    mae_pm10_model = mean_absolute_error(y_pm10_test, rf_pm10.predict(X_test))
    mae_pm10_baseline = mean_absolute_error(y_pm10_test, baseline_pm10)

    adopted = (mae_no2_model < mae_no2_baseline) and (mae_pm10_model < mae_pm10_baseline)

    if adopted:
        joblib.dump(
            {"no2": rf_no2, "pm10": rf_pm10, "features": FEATURE_COLS,
             "version": MODEL_VERSION, "trained_at": datetime.now(timezone.utc).isoformat()},
            MODEL_DIR / f"air_{district.code}.joblib",
        )
        logger.info("Modelo aire guardado para %s (adopted=True)", district.code)
    else:
        logger.info("Modelo aire NO adoptado para %s (baseline mejor)", district.code)

    return TrainResult(
        district_code=district.code,
        n_samples=len(df),
        mae_no2_model=float(mae_no2_model),
        mae_no2_baseline=float(mae_no2_baseline),
        mae_pm10_model=float(mae_pm10_model),
        mae_pm10_baseline=float(mae_pm10_baseline),
        adopted=adopted,
    )


def train_all_districts() -> list[TrainResult]:
    """Entrena todos los distritos que tengan datos suficientes."""
    results: list[TrainResult] = []
    for district in District.objects.all():
        r = train_district_model(district)
        if r:
            results.append(r)
    return results


# ──────────────────────────────────────────────
# 3. Predicción
# ──────────────────────────────────────────────
def _load_model(district: District) -> dict | None:
    path = MODEL_DIR / f"air_{district.code}.joblib"
    if not path.exists():
        return None
    return joblib.load(path)


def _latest_features(district: District) -> pd.DataFrame | None:
    """Construye la fila de features más reciente para predecir el siguiente día."""
    df = _build_dataframe(district)
    if df.empty:
        return None
    return df.tail(1)[FEATURE_COLS]


def predict_air_quality(district: District, hours: int = 24) -> list[AirPrediction]:
    """
    Predice NO2/PM10 para el distrito en el horizonte indicado.
    Por simplicidad: 1 predicción por día hasta cubrir `hours`.
    Persiste en AirPrediction y devuelve las instancias creadas.
    """

    model_bundle = _load_model(district)
    if model_bundle is None:
        logger.warning("No hay modelo entrenado para %s. Fallback a baseline.", district.code)
        return _baseline_prediction(district, hours)

    features_row = _latest_features(district)
    if features_row is None:
        logger.warning("Sin datos históricos para %s", district.code)
        return []

    # Última lectura conocida como baseline
    last_air = AirQuality.objects.filter(district=district).order_by("-period_date").first()
    last_date = last_air.period_date if last_air else datetime.now(timezone.utc).date()

    # Predecimos día a día
    steps = max(1, hours // 24)
    forecasts: list[AirPrediction] = []
    now = datetime.now(timezone.utc)

    no2_pred = float(model_bundle["no2"].predict(features_row)[0])
    pm10_pred = float(model_bundle["pm10"].predict(features_row)[0])

    for i in range(1, steps + 1):
        forecast_at = now + timedelta(days=i)
        ap = AirPrediction.objects.create(
            district=district,
            forecast_at=forecast_at,
            no2_predicted=round(no2_pred, 2),
            pm10_predicted=round(pm10_pred, 2),
            model_version=model_bundle["version"],
        )
        forecasts.append(ap)

    return forecasts


def _baseline_prediction(district: District, hours: int) -> list[AirPrediction]:
    """Fallback: repite el último valor observado."""
    last = AirQuality.objects.filter(district=district).order_by("-period_date").first()
    if not last:
        return []

    now = datetime.now(timezone.utc)
    steps = max(1, hours // 24)
    out: list[AirPrediction] = []

    for i in range(1, steps + 1):
        out.append(AirPrediction.objects.create(
            district=district,
            forecast_at=now + timedelta(days=i),
            no2_predicted=last.no2_level,
            pm10_predicted=last.pm10_level,
            model_version="baseline-v0",
        ))
    return out