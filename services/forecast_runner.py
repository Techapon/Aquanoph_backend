"""Forecast runner — หลัง analysis job: kNN 6 parameter × horizon → parameter_forecasts."""
from __future__ import annotations

from datetime import datetime

from config.constants import AnalysisConfig, DEFAULT_CONFIG


async def sweep_forecasts(
    conn,
    pond_id: str,
    now: datetime,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> int:
    """โหลดวัตถุดิบ 14 วัน → พยากรณ์ → upsert. คืนจำนวน parameter ที่เขียนได้."""
    from db.adapter import load_forecast_inputs, upsert_forecasts
    from identity.forecast.runner import forecastAll

    pond, readings, activities = await load_forecast_inputs(conn, pond_id, now, cfg)
    results = forecastAll(pond, readings, activities, now, cfg)
    if results:
        await upsert_forecasts(conn, pond_id, results)
    return len(results)
