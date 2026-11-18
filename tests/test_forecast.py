"""kNN forecast tests (pure): series alignment, similarity rank, aggregation, cold start."""
from datetime import date, datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.analysis.helpers import localTime
from identity.forecast.knn import _weightedQuantile
from identity.forecast.runner import forecastAll, forecastParameter
from identity.forecast.series import Reading, buildDaySeries, slotIndex
from identity.forecast.similarity import DayFeatures, rankDays
from identity.parameters.pond_parameter_enum import PondParameters
from tests.support.factories import makePond, t

TZ = "Asia/Bangkok"
NOW = t("2026-11-18 10:00", TZ)


def dayReadings(day: str, value: float, *, skip_slots: tuple[int, ...] = ()) -> list[Reading]:
    """48 readings (ทุก 30 นาที) ของ DO=value ในวัน local day; skip_slots = ไม่มีค่านาทีนั้น."""
    base = datetime.fromisoformat(f"{day} 00:00")
    out: list[Reading] = []
    for i in range(48):
        if i in skip_slots:
            continue
        out.append(
            Reading(
                time=t(base + timedelta(minutes=30 * i), TZ),
                values={PondParameters.DO: value},
            )
        )
    return out


def test_build_day_series_buckets_and_coverage():
    samples = [
        (t("2026-11-10 00:05", TZ), 5.0),   # slot 0
        (t("2026-11-10 00:40", TZ), 7.0),   # slot 1
        (t("2026-11-10 23:59", TZ), 9.0),   # slot 47
    ]
    series = buildDaySeries(samples, date(2026, 11, 10), TZ, DEFAULT_CONFIG)
    assert series.values[0] == 5.0
    assert series.values[1] == 7.0
    assert series.values[47] == 9.0
    assert series.values[2] is None
    assert abs(series.coverage - 3 / 48) < 1e-9


def test_gap_interpolation_one_slot_only():
    samples = [
        (t("2026-11-10 00:05", TZ), 5.0),   # slot 0
        (t("2026-11-10 01:10", TZ), 9.0),   # slot 2 (slot 1 ขาด)
    ]
    series = buildDaySeries(samples, date(2026, 11, 10), TZ, DEFAULT_CONFIG)
    assert series.values[1] == 7.0


def test_slot_alignment_uses_local_time_of_day():
    assert slotIndex(t("2026-11-17 20:00", TZ), TZ, DEFAULT_CONFIG) == 40
    assert slotIndex(t("2026-11-17 20:00", "America/New_York"), "America/New_York", DEFAULT_CONFIG) == 40


def test_weighted_quantile_basic():
    assert _weightedQuantile([1.0, 2.0, 3.0], [1.0, 1.0, 1.0], 0.5) == 2.0
    assert _weightedQuantile([1.0, 2.0, 3.0], [1.0, 1.0, 1.0], 0.25) == 1.0
    assert _weightedQuantile([1.0, 2.0, 3.0], [1.0, 1.0, 1.0], 0.75) == 3.0


def test_rank_days_prefers_similar_activity_and_water():
    today = DayFeatures(
        day=date(2026, 11, 18), water=(5.0, 5.0, 5.0), activities=(2.0, 1.0, 0.0, 0, 0, 0, 0)
    )
    similar = DayFeatures(
        day=date(2026, 11, 17), water=(5.1, 5.0, 5.2), activities=(2.0, 1.0, 0.0, 0, 0, 0, 0)
    )
    different = DayFeatures(
        day=date(2026, 11, 16), water=(2.0, 2.0, 2.0), activities=(0.0, 0.0, 0.0, 0, 0, 0, 0)
    )
    ranked = rankDays(today, [different, similar], today.day, DEFAULT_CONFIG)
    assert [n.day for n in ranked] == [similar.day, different.day]


def test_recency_penalty_breaks_equal_similarity():
    today = DayFeatures(
        day=date(2026, 11, 18), water=(5.0, 5.0, 5.0), activities=(1.0, 1.0, 0.0, 0, 0, 0, 0)
    )
    a = DayFeatures(
        day=date(2026, 11, 17), water=(5.5, 5.0, 5.5), activities=(1.0, 1.0, 0.0, 0, 0, 0, 0)
    )
    b = DayFeatures(
        day=date(2026, 11, 10), water=(5.5, 5.0, 5.5), activities=(1.0, 1.0, 0.0, 0, 0, 0, 0)
    )
    ranked = rankDays(today, [b, a], today.day, DEFAULT_CONFIG)
    assert ranked[0].day == a.day


def test_forecast_uses_past_same_clock_time():
    readings = []
    for day in ("2026-11-17", "2026-11-16", "2026-11-15", "2026-11-14", "2026-11-13"):
        readings.extend(dayReadings(day, 5.0))
    readings.extend(dayReadings("2026-11-18", 5.0)[:20])  # today 00:00–09:30

    fc = forecastParameter(PondParameters.DO, readings, (), makePond(timezone=TZ), NOW, DEFAULT_CONFIG)
    assert fc is not None
    assert len(fc.points) == 24  # 12 ชม. / 30 นาที
    at20 = next(
        p for p in fc.points
        if localTime(p.time, TZ).hour == 20 and localTime(p.time, TZ).minute == 0
    )
    assert at20.value == 5.0
    assert at20.count == 5  # K=5


def test_not_enough_days_returns_none():
    readings = []
    for day in ("2026-11-17", "2026-11-16"):
        readings.extend(dayReadings(day, 5.0))
    fc = forecastParameter(PondParameters.DO, readings, (), makePond(timezone=TZ), NOW, DEFAULT_CONFIG)
    assert fc is None


def test_missing_neighbor_slot_drops_vote_only():
    readings = []
    for day in ("2026-11-17", "2026-11-16", "2026-11-15", "2026-11-14", "2026-11-13"):
        skip = (39, 40, 41) if day == "2026-11-15" else ()  # 20:00 ของวันนั้นหาย (ช่องว่าง 3 slot)
        readings.extend(dayReadings(day, 5.0, skip_slots=skip))

    fc = forecastParameter(PondParameters.DO, readings, (), makePond(timezone=TZ), NOW, DEFAULT_CONFIG)
    assert fc is not None
    at20 = next(
        p for p in fc.points
        if localTime(p.time, TZ).hour == 20 and localTime(p.time, TZ).minute == 0
    )
    assert at20.count == 4
    assert at20.value == 5.0


def test_forecast_all_skips_parameters_without_history():
    readings = []
    for day in ("2026-11-17", "2026-11-16", "2026-11-15", "2026-11-14", "2026-11-13"):
        readings.extend(dayReadings(day, 5.0))

    results = forecastAll(makePond(timezone=TZ), readings, (), NOW, DEFAULT_CONFIG)
    assert [r.parameter for r in results] == [PondParameters.DO]
