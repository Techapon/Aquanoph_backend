"""Phase 3 PH_SWING detector tests."""
from datetime import date, datetime, timedelta

from config.constants import DEFAULT_CONFIG
from identity.diagnostic.detectors.ph_swing import detectPhSwing
from identity.parameters.pond_parameter_enum import PondParameters
from tests.support.factories import makePond, makeView, t


TZ = "Asia/Bangkok"
NOW = t("2026-10-04 12:00", TZ)


def dayViews(day: str, values: tuple[float, ...], count: int = 34, tz: str = TZ):
    base = datetime.fromisoformat(f"{day} 00:00")
    return tuple(
        makeView(PondParameters.pH, t(base + timedelta(minutes=30 * index), tz), value=values[index % len(values)])
        for index in range(count)
    )


def freshView(now: datetime = NOW):
    """Fresh pH sample clears stale gate; current local day remains excluded."""
    return makeView(PondParameters.pH, now, value=7.5)


def test_two_or_three_hit_days_create_signal_but_one_or_zero_do_not():
    hit1 = dayViews("2026-10-01", (7.0, 8.0))
    hit2 = dayViews("2026-10-02", (7.2, 8.2))
    quiet = dayViews("2026-10-03", (7.0, 7.1))
    pond = makePond(timezone=TZ)

    signal = detectPhSwing((*hit1, *hit2, *quiet, freshView()), pond, NOW)
    assert signal is not None
    assert signal.facts["hitDays"] == 2

    allHit = detectPhSwing((*hit1, *hit2, *dayViews("2026-10-03", (6.8, 7.8)), freshView()), pond, NOW)
    assert allHit is not None and allHit.facts["hitDays"] == 3
    assert detectPhSwing((*hit1, *quiet), pond, NOW) is None
    assert detectPhSwing(quiet, pond, NOW) is None


def test_any_two_complete_days_can_hit_and_float_boundary_is_stable():
    pond = makePond(timezone=TZ)
    days = (
        dayViews("2026-10-01", (7.3, 8.3)),
        dayViews("2026-10-02", (7.0, 7.1)),
        dayViews("2026-10-03", (7.0, 8.0)),
    )
    assert detectPhSwing((*days[0], *days[2], *days[1], freshView()), pond, NOW) is not None
    middleHit = dayViews("2026-10-02", (7.0, 8.0))
    assert detectPhSwing((*middleHit, *days[2], freshView()), pond, NOW) is not None

    below = dayViews("2026-10-03", (7.0, 7.99))
    assert detectPhSwing((*days[0], *below), pond, NOW) is None


def test_coverage_boundary_and_today_ignored():
    pond = makePond(timezone=TZ)
    hit1 = dayViews("2026-10-01", (7.0, 8.0), count=34)
    belowCoverage = dayViews("2026-10-02", (7.0, 8.0), count=33)
    assert detectPhSwing((*hit1, *belowCoverage), pond, NOW) is None

    todayBigSwing = dayViews("2026-10-04", (6.0, 9.0))
    assert detectPhSwing(todayBigSwing, pond, NOW) is None


def test_window_slides_and_timezone_assignment():
    pond = makePond(timezone=TZ)
    oldHit = dayViews("2026-10-01", (7.0, 8.0))
    middleHit = dayViews("2026-10-02", (7.0, 8.0))
    assert detectPhSwing((*oldHit, *middleHit, freshView()), pond, NOW) is not None

    nextDayNow = t("2026-10-05 12:00", TZ)
    assert detectPhSwing((*oldHit, *middleHit), pond, nextDayNow) is None

    # 17:30 UTC is 00:30 on next Bangkok date but 13:30 in New York.
    utc1730 = datetime(2026, 10, 1, 17, 30)
    v = makeView(PondParameters.pH, utc1730, value=7.0)
    assert detectPhSwing((v,), pond, NOW) is None

    bangkokSignal = detectPhSwing((*dayViews("2026-10-01", (7.0, 8.0)), *dayViews("2026-10-02", (7.0, 8.0)), freshView()), pond, NOW)
    assert bangkokSignal is not None
    newYork = makePond(timezone="America/New_York")
    assert detectPhSwing((*dayViews("2026-10-01", (7.0, 8.0)), *dayViews("2026-10-02", (7.0, 8.0)), freshView()), newYork, NOW) is None


def test_dst_actual_expected_readings_and_stale_gate():
    newYork = makePond(timezone="America/New_York")
    # 2026-03-08 is a 23-hour local day: 46 readings expected; 33 is >= 70%.
    dstHit = dayViews("2026-03-08", (7.0, 8.0), count=33, tz="America/New_York")
    secondHit = dayViews("2026-03-09", (7.0, 8.0), count=34, tz="America/New_York")
    now = t("2026-03-10 12:00", "America/New_York")
    assert detectPhSwing((*dstHit, *secondHit, freshView(now)), newYork, now) is not None

    stale = makeView(PondParameters.pH, now - timedelta(minutes=91), value=7.0)
    assert detectPhSwing((stale,), newYork, now) is None
    assert detectPhSwing((), newYork, now) is None
    other = makeView(PondParameters.DO, now, value=4.0)
    assert detectPhSwing((other,), newYork, now) is None


def test_unsorted_duplicate_input_facts_and_determinism():
    pond = makePond(timezone=TZ)
    hit1 = dayViews("2026-10-01", (7.0, 8.0))
    hit2 = dayViews("2026-10-02", (7.0, 8.0))
    duplicate = hit2[0]
    raw = (*reversed(hit2), duplicate, *reversed(hit1), freshView())
    before = tuple(raw)
    first = detectPhSwing(raw, pond, NOW)
    second = detectPhSwing(raw, pond, NOW)

    assert first == second
    assert raw == before
    assert first is not None
    assert first.sourceId == "PH_SWING:pond_1"
    assert first.sourceType.value == "detector"
    assert first.code == "PH_SWING"
    assert first.parameter == PondParameters.pH
    assert first.active is True
    assert first.riskStart is None
    assert first.riskEnd is None
    assert first.peakSeverity is None
    assert first.lastSeverity is None
    assert first.scope is None
    assert first.facts["hitDays"] == 2
    assert first.facts["windowDays"] == 3
    assert tuple(d["date"] for d in first.facts["days"]) == (
        date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3),
    )
    assert first.facts["days"][0] == {
        "date": date(2026, 10, 1),
        "swing": 1.0,
        "coverage": round(34 / 48, 6),
        "readingCount": 34,
        "hit": True,
    }
    assert first.facts["days"][2] == {
        "date": date(2026, 10, 3),
        "swing": 0.0,
        "coverage": 0.0,
        "readingCount": 0,
        "hit": False,
    }
