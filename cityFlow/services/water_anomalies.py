# cityFlow/services/water_anomalies.py
"""
Detección de anomalías en consumo de agua.

Método principal (v1): z-score robusto sobre la desviación respecto al
consumo esperado (mediana móvil por distrito + día de la semana).
Comparación con IsolationForest cuando hay suficientes datos.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from cityFlow.models import District, WaterConsumption, WaterPrediction

from cityFlow.services.alert_dispatcher import create_alert

logger = logging.getLogger(__name__)

MODEL_VERSION = "water-v1"

# Umbrales de decisión (ajustables)
Z_THRESHOLD = 3.0          # desviaciones estándar robustas
MIN_DEVIATION_PCT = 25.0   # % mínimo de desviación para considerar anomalía


# ──────────────────────────────────────────────
# 1. Consumo esperado (mediana móvil)
# ──────────────────────────────────────────────
def _expected_consumption(df: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    Estima el consumo esperado como mediana móvil centrada de las últimas
    `window` observaciones (excluyendo la actual) del mismo distrito.
    """
    return df["consumption_m3"].shift(1).rolling(window=window, min_periods=3).median()


def _robust_zscore(series: pd.Series) -> pd.Series:
    """Z-score robusto basado en MAD."""
    median = series.median()
    mad = (series - median).abs().median()
    scale = 1.4826 * mad if mad > 0 else series.std(ddof=0)
    if not scale or np.isnan(scale):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - median) / scale


# ──────────────────────────────────────────────
# 2. Análisis por distrito
# ──────────────────────────────────────────────
@dataclass
class AnomalyResult:
    district_code: str
    total_readings: int
    anomalies_detected: int
    predictions_created: int

def analyze_district(district: District, lookback_days: int = 90) -> AnomalyResult:

    """
        Analiza el historial reciente del distrito, detecta anomalías y
        persiste WaterPrediction para las lecturas anómalas.
        """
    qs = WaterConsumption.objects.filter(district=district).order_by("period_date")
    df = pd.DataFrame(list(qs.values("id", "period_date", "consumption_m3")))

    if df.empty or len(df) < 5:
        return AnomalyResult(district.code, len(df), 0, 0)

    # ─── FIX: convertir Decimal → float ANTES de operar ───
    df["consumption_m3"] = df["consumption_m3"].astype(float)

    df["period_date"] = pd.to_datetime(df["period_date"])
    df["expected"] = _expected_consumption(df)
    # ...

    # Desviación porcentual
    df["deviation_pct"] = np.where(
        df["expected"] > 0,
        (df["consumption_m3"] - df["expected"]) / df["expected"] * 100.0,
        np.nan,
    )

    # Z-score robusto sobre la desviación
    df["z"] = _robust_zscore(df["deviation_pct"].fillna(0))

    # Criterio: |z| > umbral Y |deviation_pct| > mínimo
    df["is_anomaly"] = (
        (df["z"].abs() > Z_THRESHOLD) &
        (df["deviation_pct"].abs() > MIN_DEVIATION_PCT)
    )

    # anomaly_score normalizado [0,1]
    df["anomaly_score"] = (df["z"].abs() / (Z_THRESHOLD * 2)).clip(0, 1)

    anomalies = df[df["is_anomaly"] & df["expected"].notna()]
    created = 0

    for pred, row in anomalies.iterrows():
        pred, was_created = WaterPrediction.objects.update_or_create(
            district=district,
            target_date=row["period_date"].date(),
            defaults={
                "expected_consumption_m3": round(float(row["expected"]), 2),
                "observed_consumption_m3": round(float(row["consumption_m3"]), 2),
                "deviation_pct": round(float(row["deviation_pct"]), 2),
                "anomaly_score": round(float(row["anomaly_score"]), 4),
                "is_anomaly": True,
                "model_version": MODEL_VERSION,
            },
        )
        if was_created:
            created += 1
            create_alert(                                      # ← NUEVO
                district=district,
                alert_type="water_anomaly",
                severity="warning" if abs(row["deviation_pct"]) < 50 else "critical",
                title=f"Consumo anómalo en {district.name}",
                message=(
                    f"Consumo observado {row['consumption_m3']:.0f} m³ vs "
                    f"esperado {row['expected']:.0f} m³ "
                    f"({row['deviation_pct']:+.1f}%)"
                ),
                related_object_id=pred.id,
            )

    return AnomalyResult(district.code, len(df), int(anomalies.shape[0]), created)


def analyze_all_districts() -> list[AnomalyResult]:
    return [analyze_district(d) for d in District.objects.all()]