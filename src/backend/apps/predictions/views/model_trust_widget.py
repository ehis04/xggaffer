from __future__ import annotations

import logging
from math import log

from django.db.models import Count, Q
from rest_framework.request import Request

from apps.predictions.models import OddsAccuracyStats
from apps.predictions.utils.league_codes import to_competition_code, to_understat_code
from apps.predictions.utils.widget_freshness import get_engine_widget_freshness
from apps.predictions.views.widget_base import WidgetBaseView

_logger = logging.getLogger(__name__)

MIN_RESOLVED_FOR_DISPLAY = 10
RECENT_FORM_COUNT = 50
BIGGEST_MISSES_LIMIT = 5
CONFIDENCE_BANDS = ["high", "medium", "low"]
CONFIDENCE_BUCKET_EDGES = [0.33, 0.40, 0.47, 0.54, 0.61, 0.68, 0.75, 0.82, 1.01]
OUTCOME_LABEL = {"H": "Home Win", "D": "Draw", "A": "Away Win"}
EPSILON = 1e-9


def _prob_for_outcome(record, outcome: str) -> float:
    if outcome == "H":
        return record.predicted_home_prob
    if outcome == "A":
        return record.predicted_away_prob
    return record.predicted_draw_prob


def _build_record_row(m) -> dict:
    max_prob = max(m.predicted_home_prob, m.predicted_draw_prob, m.predicted_away_prob)
    actual_prob = _prob_for_outcome(m, m.actual_result)
    return {
        "home_team": m.home_team,
        "away_team": m.away_team,
        "predicted_outcome": OUTCOME_LABEL.get(m.predicted_outcome, m.predicted_outcome),
        "actual_result": OUTCOME_LABEL.get(m.actual_result, m.actual_result),
        "confidence_band": m.confidence_band,
        "predicted_at": m.predicted_at.isoformat(),
        "predicted_home_prob": m.predicted_home_prob,
        "predicted_draw_prob": m.predicted_draw_prob,
        "predicted_away_prob": m.predicted_away_prob,
        "max_confidence": round(max_prob, 4),
        "actual_outcome_prob": round(actual_prob, 4),
        "off_by": round(abs(max_prob - actual_prob), 4),
    }


def _clamp_prob(prob: float) -> float:
    return max(EPSILON, min(1.0 - EPSILON, prob))


def _multiclass_brier_for_record(record) -> float:
    probs = {
        "H": record.predicted_home_prob,
        "D": record.predicted_draw_prob,
        "A": record.predicted_away_prob,
    }
    target = record.actual_result
    squared_error_sum = 0.0
    for outcome, prob in probs.items():
        y = 1.0 if outcome == target else 0.0
        squared_error_sum += (prob - y) ** 2
    # Keep this in [0, 1] by averaging over the 3 outcomes.
    return squared_error_sum / 3.0


def _weighted_avg_odds_stat(rows, attr: str) -> float | None:
    total_weight = sum(r.total_evaluated or 0 for r in rows if getattr(r, attr) is not None)
    if total_weight == 0:
        return None
    return sum((r.total_evaluated or 0) * getattr(r, attr) for r in rows if getattr(r, attr) is not None) / total_weight


def _resolve_league_aliases(raw_league_code: str | None) -> list[str]:
    if not raw_league_code:
        return []

    league_code = raw_league_code.strip()
    if not league_code:
        return []

    variants: list[str] = []

    # Keep the original user-provided value first to avoid changing expected behavior.
    if league_code not in variants:
        variants.append(league_code)

    as_competition = to_competition_code(league_code)
    if as_competition and as_competition not in variants:
        variants.append(as_competition)

    as_understat = to_understat_code(league_code)
    if as_understat and as_understat not in variants:
        variants.append(as_understat)

    return variants


class ModelTrustWidgetView(WidgetBaseView):
    widget_intent = "model-trust"

    def get_widget_data(self, request: Request) -> dict:
        league_code = request.query_params.get("league_code", "").strip() or None
        league_aliases = _resolve_league_aliases(league_code)

        from apps.predictions.models import PredictionRecord

        base_qs = PredictionRecord.objects.filter(actual_result__isnull=False)
        if league_aliases:
            alias_filter = Q()
            for alias in league_aliases:
                alias_filter |= Q(league_code__iexact=alias)
            base_qs = base_qs.filter(alias_filter)

        total_resolved = base_qs.count()

        freshness = get_engine_widget_freshness("outcome")

        if total_resolved < MIN_RESOLVED_FOR_DISPLAY:
            if league_code:
                cold_start_note = (
                    f"Not enough resolved predictions for {league_code} yet. "
                    "This view unlocks after at least 10 resolved predictions."
                )
            else:
                cold_start_note = "Prediction review data will appear once match results are logged."

            # Hide the freshness badge during cold-start — ELO staleness is
            # irrelevant here since this view is driven by resolved PredictionRecords.
            cold_start_freshness = {
                **freshness,
                "staleness_status": "no_coverage",
            }

            return {
                "widget_type": "model_trust",
                "data": None,
                "explanation": {},
                "confidence": {"score": 0.0, "band": "low"},
                "freshness": cold_start_freshness,
                "summary": {
                    "cold_start_note": cold_start_note,
                },
            }

        correct_total = base_qs.filter(correct=True).count()
        overall_accuracy = correct_total / total_resolved

        accuracy_by_band = []
        for band in CONFIDENCE_BANDS:
            band_qs = base_qs.filter(confidence_band=band)
            band_total = band_qs.count()
            band_correct = band_qs.filter(correct=True).count()
            accuracy_by_band.append({
                "band": band,
                "total": band_total,
                "correct_count": band_correct,
                "accuracy": band_correct / band_total if band_total > 0 else None,
            })

        league_rows = list(
            base_qs.values("league_code").annotate(
                total=Count("id"),
                correct_count=Count("id", filter=Q(correct=True)),
            )
        )
        accuracy_by_league = [
            {
                "league_code": row["league_code"],
                "total": row["total"],
                "correct_count": row["correct_count"],
                "accuracy": row["correct_count"] / row["total"] if row["total"] > 0 else 0.0,
            }
            for row in league_rows
        ]

        recent_qs = list(base_qs.order_by("-resolved_at")[:RECENT_FORM_COUNT])
        recent_correct = sum(1 for r in recent_qs if r.correct)
        recent_count = len(recent_qs)
        recent_form = {
            "count": recent_count,
            "accuracy": recent_correct / recent_count if recent_count > 0 else 0.0,
        }

        misses_qs = base_qs.filter(
            correct=False,
            confidence_band="high",
        ).order_by("-predicted_at")[:BIGGEST_MISSES_LIMIT]

        biggest_misses = [_build_record_row(m) for m in misses_qs]

        hits_qs = base_qs.filter(
            correct=True,
            confidence_band="high",
        ).order_by("-predicted_at")[:BIGGEST_MISSES_LIMIT]

        biggest_hits = [_build_record_row(m) for m in hits_qs]

        latest_resolved = base_qs.order_by("-resolved_at").first()
        if latest_resolved and latest_resolved.resolved_at:
            freshness["snapshot_published_at"] = latest_resolved.resolved_at.isoformat()
        # Trust page freshness is driven by resolved PredictionRecord data, not ELO.
        freshness["is_stale"] = False
        freshness["is_degraded"] = False
        freshness["cascade_degraded"] = False
        freshness["cascade_reason"] = None

        odds_qs = OddsAccuracyStats.objects.all()
        if league_aliases:
            odds_filter = Q()
            for alias in league_aliases:
                odds_filter |= Q(league__iexact=alias)
            odds_qs = odds_qs.filter(odds_filter)

        odds_rows = list(odds_qs)
        total_eval = sum(r.total_evaluated or 0 for r in odds_rows)
        market_correct_total = sum(r.market_correct_count or 0 for r in odds_rows)
        market_comparison = {
            "market_accuracy": round(market_correct_total / total_eval, 4) if total_eval > 0 else None,
            "model_accuracy_vs_market": round(sum(r.model_wins or 0 for r in odds_rows) / total_eval, 4) if total_eval > 0 else None,
            "total_evaluated": total_eval,
        }

        market_confidence_real = _weighted_avg_odds_stat(odds_rows, "market_confidence")
        market_brier_real = _weighted_avg_odds_stat(odds_rows, "market_brier_score")
        market_log_loss_real = _weighted_avg_odds_stat(odds_rows, "market_log_loss")

        all_resolved = list(base_qs.only(
            "predicted_home_prob", "predicted_draw_prob", "predicted_away_prob", "correct", "actual_result"
        ))

        model_confidence_avg = 0.0
        model_brier_avg = 0.0
        model_log_loss_avg = 0.0
        if all_resolved:
            confidences = [
                max(r.predicted_home_prob, r.predicted_draw_prob, r.predicted_away_prob)
                for r in all_resolved
            ]
            brier_values = [_multiclass_brier_for_record(r) for r in all_resolved]
            log_losses = [
                -log(_clamp_prob(_prob_for_outcome(r, r.actual_result)))
                for r in all_resolved
            ]
            model_confidence_avg = sum(confidences) / len(confidences)
            model_brier_avg = sum(brier_values) / len(brier_values)
            model_log_loss_avg = sum(log_losses) / len(log_losses)

        random_accuracy = 1.0 / 3.0
        random_confidence = 1.0 / 3.0
        random_brier = 2.0 / 9.0
        random_log_loss = -log(1.0 / 3.0)

        calibration_factor_plot = {
            "factors": [
                {"key": "accuracy", "label": "Accuracy", "higher_is_better": True},
                {"key": "confidence", "label": "Confidence", "higher_is_better": True},
                {"key": "brier_score", "label": "Brier score", "higher_is_better": False},
                {"key": "log_loss", "label": "Log loss", "higher_is_better": False},
            ],
            "series": [
                {
                    "key": "random",
                    "label": "Random baseline",
                    "color": "grey",
                    "values": {
                        "accuracy": round(random_accuracy, 4),
                        "confidence": round(random_confidence, 4),
                        "brier_score": round(random_brier, 4),
                        "log_loss": round(random_log_loss, 4),
                    },
                },
                {
                    "key": "market",
                    "label": "Market",
                    "color": "red",
                    "values": {
                        "accuracy": round(market_comparison["market_accuracy"], 4)
                        if market_comparison["market_accuracy"] is not None
                        else None,
                        "confidence": round(market_confidence_real, 4)
                        if market_confidence_real is not None
                        else None,
                        "brier_score": round(market_brier_real, 4)
                        if market_brier_real is not None
                        else None,
                        "log_loss": round(market_log_loss_real, 4)
                        if market_log_loss_real is not None
                        else None,
                    },
                },
                {
                    "key": "model",
                    "label": "Model",
                    "color": "green",
                    "values": {
                        "accuracy": round(overall_accuracy, 4),
                        "confidence": round(model_confidence_avg, 4),
                        "brier_score": round(model_brier_avg, 4),
                        "log_loss": round(model_log_loss_avg, 4),
                    },
                },
            ],
        }

        confidence_distribution = []
        for i in range(len(CONFIDENCE_BUCKET_EDGES) - 1):
            lo = CONFIDENCE_BUCKET_EDGES[i]
            hi = CONFIDENCE_BUCKET_EDGES[i + 1]
            bucket_records = [
                r for r in all_resolved
                if lo <= max(r.predicted_home_prob, r.predicted_draw_prob, r.predicted_away_prob) < hi
            ]
            total_b = len(bucket_records)
            correct_b = sum(1 for r in bucket_records if r.correct)
            confidence_distribution.append({
                "bucket_min": lo,
                "bucket_max": hi if hi < 1.01 else 1.0,
                "total": total_b,
                "correct_count": correct_b,
                "accuracy": round(correct_b / total_b, 4) if total_b > 0 else None,
            })

        data = {
            "overall_accuracy": overall_accuracy,
            "total_resolved": total_resolved,
            "accuracy_by_band": accuracy_by_band,
            "accuracy_by_league": accuracy_by_league,
            "recent_form": recent_form,
            "biggest_misses": biggest_misses,
            "biggest_hits": biggest_hits,
            "market_comparison": market_comparison,
            "calibration_factor_plot": calibration_factor_plot,
            "confidence_distribution": confidence_distribution,
        }

        return {
            "widget_type": "model_trust",
            "data": data,
            "explanation": {},
            "confidence": {"score": overall_accuracy, "band": "high"},
            "freshness": freshness,
            "summary": {},
        }