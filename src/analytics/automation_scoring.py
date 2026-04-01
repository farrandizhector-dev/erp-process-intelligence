"""Automation opportunity scoring for P2P activities.

Implements the composite scoring model from CONTEXT.md Section 9.5.

Each activity receives scores on 6 dimensions (all normalized 0-1):
  1. volume_score        — how frequently is this activity executed?
  2. batch_gap_score     — how much room is there for automation (1 - batch_ratio)?
  3. input_uniformity    — how consistent is the activity's context?
  4. timing_regularity   — how predictable is the execution timing?
  5. error_reduction     — is this activity associated with rework?
  6. wait_reduction      — does this activity follow long waits?

Composite: weighted sum per AUTOMATION_WEIGHTS in config.py.
"""

from __future__ import annotations

import logging
from math import log2

import polars as pl

from src import config

logger = logging.getLogger(__name__)

DATASET_MONTHS = 24.0  # BPI 2019 covers Jan 2018 – Dec 2019


def shannon_entropy(distribution: dict[str, int]) -> float:
    """Compute normalized Shannon entropy of a frequency distribution.

    Returns 0 for single-value or empty distributions, 1 for uniform.

    Args:
        distribution: Mapping of category → count.

    Returns:
        Normalized entropy in [0, 1].
    """
    total = sum(distribution.values())
    if total == 0:
        return 0.0
    probs = [count / total for count in distribution.values() if count > 0]
    if len(probs) <= 1:
        return 0.0
    raw_entropy = -sum(p * log2(p) for p in probs)
    max_entropy = log2(len(probs))
    return raw_entropy / max_entropy if max_entropy > 0 else 0.0


def compute_automation_opportunities(
    events: pl.DataFrame,
    cases: pl.DataFrame,
) -> pl.DataFrame:
    """Compute fact_automation_opportunities for all activities.

    Args:
        events: Silver events (case_id, activity, resource, resource_type,
                time_since_prev_event, timestamp).
        cases: Silver cases (case_id, variant_id) — used for rework join.

    Returns:
        fact_automation_opportunities DataFrame (42 rows for BPI 2019).
    """
    logger.info("Computing automation opportunity scores for %d activities...",
                events["activity"].n_unique())

    df = events.sort(["case_id", "timestamp"])

    # Convert Duration → float seconds once upfront to avoid map_elements on Duration
    df = df.with_columns(
        pl.col("time_since_prev_event")
        .dt.total_seconds()
        .cast(pl.Float64)
        .alias("_wait_s")
    )

    # ------------------------------------------------------------------
    # Base counts
    # ------------------------------------------------------------------
    base = (
        df.group_by("activity")
        .agg(
            [
                pl.len().cast(pl.UInt64).alias("total_executions"),
                (pl.col("resource_type") == "batch").sum().cast(pl.UInt64)
                .alias("batch_executions"),
                (pl.col("resource_type") == "human").sum().cast(pl.UInt64)
                .alias("human_executions"),
                pl.col("case_id").n_unique().cast(pl.UInt64).alias("case_count"),
                pl.col("_wait_s").drop_nulls().mean().alias("_avg_wait_s"),
                pl.col("_wait_s").drop_nulls().median().alias("_median_wait_s"),
                pl.col("_wait_s").drop_nulls().std().alias("_std_wait_s"),
            ]
        )
    )

    # batch_ratio
    base = base.with_columns(
        (pl.col("batch_executions").cast(pl.Float64) / pl.col("total_executions").cast(pl.Float64))
        .alias("batch_ratio")
    )

    # ------------------------------------------------------------------
    # Predecessor entropy (input uniformity proxy)
    # ------------------------------------------------------------------
    df_with_prev = df.with_columns(
        pl.col("activity").shift(1).over("case_id").alias("prev_activity")
    ).filter(pl.col("prev_activity").is_not_null())

    pred_entropy = (
        df_with_prev.group_by(["activity", "prev_activity"])
        .agg(pl.len().alias("count"))
        .group_by("activity")
        .agg([
            pl.col("prev_activity").alias("_pred_acts"),
            pl.col("count").alias("_pred_cnts"),
        ])
        .with_columns(
            pl.struct(["_pred_acts", "_pred_cnts"])
            .map_elements(
                lambda s: shannon_entropy(
                    dict(zip(s["_pred_acts"], s["_pred_cnts"], strict=False))
                ),
                return_dtype=pl.Float64,
            )
            .alias("predecessor_entropy")
        )
        .select(["activity", "predecessor_entropy"])
    )

    # Successor entropy
    df_with_next = df.with_columns(
        pl.col("activity").shift(-1).over("case_id").alias("next_activity")
    ).filter(pl.col("next_activity").is_not_null())

    succ_entropy = (
        df_with_next.group_by(["activity", "next_activity"])
        .agg(pl.len().alias("count"))
        .group_by("activity")
        .agg([
            pl.col("next_activity").alias("_succ_acts"),
            pl.col("count").alias("_succ_cnts"),
        ])
        .with_columns(
            pl.struct(["_succ_acts", "_succ_cnts"])
            .map_elements(
                lambda s: shannon_entropy(
                    dict(zip(s["_succ_acts"], s["_succ_cnts"], strict=False))
                ),
                return_dtype=pl.Float64,
            )
            .alias("successor_entropy")
        )
        .select(["activity", "successor_entropy"])
    )

    # Event order position CV (coefficient of variation)
    position_cv = (
        df.group_by(["case_id", "activity"])
        .agg(pl.col("event_order").mean().alias("pos"))
        .group_by("activity")
        .agg(
            [
                pl.col("pos").std().alias("pos_std"),
                pl.col("pos").mean().alias("pos_mean"),
            ]
        )
        .with_columns(
            pl.when(pl.col("pos_mean") > 0)
            .then(pl.col("pos_std") / pl.col("pos_mean"))
            .otherwise(pl.lit(0.0))
            .alias("position_cv")
        )
        .select(["activity", "position_cv"])
    )

    # ------------------------------------------------------------------
    # Rework association (error_reduction)
    # ------------------------------------------------------------------
    rework_cases = events.group_by(["case_id", "activity"]).agg(
        pl.len().alias("occ")
    ).filter(pl.col("occ") > 1).select("case_id").unique()

    act_rework = (
        events.join(rework_cases.with_columns(pl.lit(True).alias("has_rework")),
                    on="case_id", how="left")
        .with_columns(pl.col("has_rework").fill_null(False))
        .group_by("activity")
        .agg(
            [
                pl.col("has_rework").mean().alias("error_rate"),
            ]
        )
    )

    # ------------------------------------------------------------------
    # Assemble all dimensions
    # ------------------------------------------------------------------
    scored = (
        base
        .join(pred_entropy, on="activity", how="left")
        .join(succ_entropy, on="activity", how="left")
        .join(position_cv, on="activity", how="left")
        .join(act_rework, on="activity", how="left")
    )

    scored = scored.with_columns(
        [
            pl.col("predecessor_entropy").fill_null(0.0),
            pl.col("successor_entropy").fill_null(0.0),
            pl.col("position_cv").fill_null(0.0),
            pl.col("error_rate").fill_null(0.0),
        ]
    )

    # ------------------------------------------------------------------
    # Normalize scores to [0, 1]
    # ------------------------------------------------------------------
    total_min = scored["total_executions"].min()
    total_max = scored["total_executions"].max()
    avg_wait_max = scored["_avg_wait_s"].max()

    scored = scored.with_columns(
        [
            # 1. Volume score
            pl.when(total_max > total_min)
            .then(
                (pl.col("total_executions").cast(pl.Float64) - total_min)
                / (total_max - total_min)
            )
            .otherwise(pl.lit(0.5))
            .alias("volume_score"),

            # 2. Batch gap score
            (pl.lit(1.0) - pl.col("batch_ratio")).alias("batch_gap_score"),

            # 3. Input uniformity (low entropy + low position CV = high uniformity)
            (pl.lit(1.0) - (
                (pl.col("predecessor_entropy") + pl.col("successor_entropy")
                 + pl.col("position_cv"))
                / pl.lit(3.0)
            ).clip(0.0, 1.0)).alias("input_uniformity"),

            # 4. Timing regularity (low CV = predictable = high score)
            pl.when(pl.col("_median_wait_s") > 0)
            .then(
                pl.lit(1.0) - (pl.col("_std_wait_s") / pl.col("_median_wait_s")).clip(0.0, 1.0)
            )
            .otherwise(pl.lit(1.0))
            .alias("timing_regularity"),

            # 5. Error reduction potential
            (pl.col("error_rate") * pl.lit(2.0)).clip(0.0, 1.0).alias("error_reduction"),

            # 6. Wait reduction potential
            pl.when(avg_wait_max > 0)
            .then(pl.col("_avg_wait_s") / avg_wait_max)
            .otherwise(pl.lit(0.0))
            .alias("wait_reduction"),
        ]
    )

    # ------------------------------------------------------------------
    # Composite score
    # ------------------------------------------------------------------
    w = config.AUTOMATION_WEIGHTS
    scored = scored.with_columns(
        (
            pl.col("volume_score") * w["volume_score"]
            + pl.col("batch_gap_score") * w["batch_gap_score"]
            + pl.col("input_uniformity") * w["input_uniformity"]
            + pl.col("timing_regularity") * w["timing_regularity"]
            + pl.col("error_reduction") * w["error_reduction"]
            + pl.col("wait_reduction") * w["wait_reduction"]
        ).alias("automation_score")
    )

    # ------------------------------------------------------------------
    # Tier assignment
    # ------------------------------------------------------------------
    already_batch_threshold = config.AUTOMATION_ALREADY_BATCH_THRESHOLD
    scored = scored.with_columns(
        pl.when(pl.col("batch_ratio") >= already_batch_threshold)
        .then(pl.lit("not_recommended"))
        .when(pl.col("automation_score") >= config.AUTOMATION_TIER_THRESHOLDS["quick_win"])
        .then(pl.lit("quick_win"))
        .when(pl.col("automation_score") >= config.AUTOMATION_TIER_THRESHOLDS["medium_effort"])
        .then(pl.lit("medium_effort"))
        .when(pl.col("automation_score") >= config.AUTOMATION_TIER_THRESHOLDS["complex"])
        .then(pl.lit("complex"))
        .otherwise(pl.lit("not_recommended"))
        .alias("automation_tier")
    )

    # ------------------------------------------------------------------
    # Estimated hours saved per month
    # ------------------------------------------------------------------
    max_minutes = config.MAX_HUMAN_PROCESSING_MINUTES
    scored = scored.with_columns(
        [
            (pl.col("_median_wait_s") / 60.0).clip(0.0, max_minutes).alias("_avg_human_min"),
        ]
    )
    scored = scored.with_columns(
        (
            (pl.col("human_executions").cast(pl.Float64) / DATASET_MONTHS)
            * pl.col("_avg_human_min")
            / 60.0
        ).alias("estimated_hours_saved_monthly")
    )

    # ------------------------------------------------------------------
    # Select final columns
    # ------------------------------------------------------------------
    result = scored.select(
        [
            "activity",
            "total_executions",
            "batch_executions",
            "human_executions",
            "batch_ratio",
            "case_count",
            "volume_score",
            "batch_gap_score",
            "input_uniformity",
            "timing_regularity",
            "error_reduction",
            "wait_reduction",
            "automation_score",
            "automation_tier",
            "estimated_hours_saved_monthly",
        ]
    ).sort("automation_score", descending=True)

    # Log top candidates
    top = result.filter(pl.col("automation_tier").is_in(["quick_win", "medium_effort"]))
    logger.info(
        "Automation scoring complete: %d activities; %d quick_win, %d medium_effort",
        len(result),
        result.filter(pl.col("automation_tier") == "quick_win").height,
        result.filter(pl.col("automation_tier") == "medium_effort").height,
    )
    for row in top.head(5).iter_rows(named=True):
        logger.info(
            "  %-45s score=%.3f tier=%s est_h/mo=%.0f",
            row["activity"],
            row["automation_score"],
            row["automation_tier"],
            row["estimated_hours_saved_monthly"],
        )
    return result


