"""Recommendation catalog: drafts from signals."""
from identity.analysis.models import Signal, SignalSource, PondInfo, ProposedActivity, SourceRef
from identity.recommendation.types import RecDraft
from config.constants import AnalysisConfig, DEFAULT_CONFIG
from identity.analysis.helpers import localDate, localDayBounds, nightWindowFor
from identity.parameters.pond_parameter_enum import PondParameters
from identity.units.threshold_units.threshold_level.threshold_level import ThresholdLevelType
from identity.units.severity_units.severity_level.severity_level_enum import SeverityLevelType
from identity.analysis.severity_view import severityRank
from typing import Iterable
from datetime import datetime, timedelta

from identity.recommendation.catalog import aerate, water_change, add_alkalinity


def existingOpenFor(snapshot, entryId, sources):
    for rec in getattr(snapshot, "recommendations", ()):
        if rec.entryId != entryId:
            continue
        if getattr(rec, "status", None) not in ("pending", "snoozed"):
            continue
        if any(s in getattr(rec, "sources", ()) for s in sources):
            return rec
    return None


def buildDrafts(signals, snapshot, now, cfg=DEFAULT_CONFIG):
    drafts: list[RecDraft] = []
    drafts.extend(aerate.build(signals, snapshot, now, cfg))
    drafts.extend(water_change.build(signals, snapshot, now, cfg))
    drafts.extend(add_alkalinity.build(signals, snapshot, now, cfg))
    drafts.sort(key=lambda d: d.dedupeKey)
    return tuple(drafts)
