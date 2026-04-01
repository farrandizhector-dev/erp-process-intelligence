"""Predictive SLA risk model for P2P cases.

Binary LightGBM classifier: will a case exceed the P75 duration for its flow type?
Uses only features available at case creation time (no data leakage).

Split strategy: stratified random split (80/20) rather than temporal, because
the dataset covers only Jan–Dec 2018 (with a tiny Jan 2019 tail). A temporal
split sends Q4 cases to the test set, but those cases are right-censored —
their final duration wasn't observed yet within the dataset window. This
creates severe class imbalance (1.8% positive in test vs 31% in train),
making temporal evaluation unreliable. A stratified random split preserves
the 25% positive rate in both folds and gives honest generalization metrics.
See docs/modeling_notes.md for full discussion.

See CONTEXT.md Section 9.6 for feature and methodology notes.
"""

from __future__ import annotations

import logging
import pickle

import numpy as np
import polars as pl
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedShuffleSplit

from src import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fixed category mappings (label names only — no statistics, no leakage)
# ---------------------------------------------------------------------------
_FLOW_TYPE_MAP: dict[str, int] = {
    "2way": 0,
    "3way_invoice_after_gr": 1,
    "3way_invoice_before_gr": 2,
    "consignment": 3,
}
_ITEM_TYPE_MAP: dict[str, int] = {
    "Consignment": 0,
    "Limit": 1,
    "Service": 2,
    "Standard": 3,
    "Subcontracting": 4,
    "Third-party": 5,
}
_DOC_TYPE_MAP: dict[str, int] = {
    "EC Purchase order": 0,
    "Framework order": 1,
    "Standard PO": 2,
}
_COMPANY_MAP: dict[str, int] = {
    "companyID_0000": 0,
    "companyID_0001": 1,
    "companyID_0002": 2,
    "companyID_0003": 3,
}

FEATURE_NAMES = [
    "flow_type_enc",
    "company_enc",
    "vendor_freq",
    "item_type_enc",
    "document_type_enc",
    "gr_based_iv",
    "goods_receipt",
    "start_month",
    "start_quarter",
    "start_dow",
]


def _engineer_features(
    df: pl.DataFrame,
    vendor_freq_map: dict[str, int] | None = None,
) -> tuple[pl.DataFrame, dict[str, int]]:
    """Add encoded feature columns and compute/apply vendor frequency encoding.

    Args:
        df: fact_case_summary rows (case_start ≥ 2018).
        vendor_freq_map: Vendor→count from training set. If None, computed from
            df (use only on training data to avoid leakage).

    Returns:
        Tuple of (enriched DataFrame, vendor_freq_map).
    """
    if vendor_freq_map is None:
        vf = df.group_by("vendor").agg(pl.len().alias("vfreq"))
        vendor_freq_map = dict(
            zip(vf["vendor"].to_list(), vf["vfreq"].to_list(), strict=False)
        )

    df = df.with_columns([
        pl.col("flow_type").replace(_FLOW_TYPE_MAP, default=-1)
        .cast(pl.Int32).alias("flow_type_enc"),

        pl.col("company").replace(_COMPANY_MAP, default=-1)
        .cast(pl.Int32).alias("company_enc"),

        pl.col("vendor").replace(vendor_freq_map, default=1)
        .cast(pl.Int32).alias("vendor_freq"),

        pl.col("item_type").replace(_ITEM_TYPE_MAP, default=-1)
        .cast(pl.Int32).alias("item_type_enc"),

        pl.col("document_type").replace(_DOC_TYPE_MAP, default=-1)
        .cast(pl.Int32).alias("document_type_enc"),

        pl.col("gr_based_iv").cast(pl.Int32),
        pl.col("goods_receipt").cast(pl.Int32),

        pl.col("case_start").dt.month().cast(pl.Int32).alias("start_month"),
        pl.col("case_start").dt.quarter().cast(pl.Int32).alias("start_quarter"),
        pl.col("case_start").dt.weekday().cast(pl.Int32).alias("start_dow"),
    ])

    return df, vendor_freq_map


def build_sla_risk_model() -> int:
    """Train LightGBM SLA risk classifier and write fact_sla_risk.parquet.

    Reads fact_case_summary.parquet, trains on a stratified 80/20 random
    split, evaluates on held-out set, writes predictions for all cases
    and model metrics to pickle.

    Returns:
        Number of rows written to fact_sla_risk.parquet.

    Raises:
        FileNotFoundError: If gold parquet files are missing.
    """
    if not config.GOLD_FACT_CASE_SUMMARY.exists():
        raise FileNotFoundError(
            f"Gold summary not found: {config.GOLD_FACT_CASE_SUMMARY}. "
            "Run --phase gold first."
        )

    logger.info("Loading fact_case_summary for SLA risk modeling...")
    cases = pl.read_parquet(config.GOLD_FACT_CASE_SUMMARY)

    # Filter out 264 cases with anomalous 1948 timestamps
    cases = cases.filter(pl.col("case_start").dt.year() >= 2018)
    logger.info("Cases for modeling (2018+): %d", len(cases))

    # ------------------------------------------------------------------
    # Binary target: above-P75 duration per flow type
    # ------------------------------------------------------------------
    cases = cases.with_columns(
        (pl.col("sla_risk") != "low").cast(pl.Int32).alias("target")
    )
    pos_rate = float(cases["target"].mean())
    logger.info(
        "Target: above-P75 duration per flow_type | positive rate: %.1f%%",
        pos_rate * 100,
    )

    # ------------------------------------------------------------------
    # Stratified random split (80/20) — preserves class balance in both folds
    # Temporal split is not used: Q4 2018 cases are right-censored within
    # the dataset window, collapsing test-set positive rate to ~2%.
    # ------------------------------------------------------------------
    n_total = len(cases)
    y_all = cases["target"].to_numpy()

    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    train_idx, test_idx = next(sss.split(np.zeros(n_total), y_all))

    train = cases[train_idx.tolist()]
    test = cases[test_idx.tolist()]

    logger.info(
        "Stratified split: train=%d (%.1f%% positive), test=%d (%.1f%% positive)",
        len(train), float(train["target"].mean()) * 100,
        len(test), float(test["target"].mean()) * 100,
    )

    # ------------------------------------------------------------------
    # Feature engineering (vendor freq computed on train only)
    # ------------------------------------------------------------------
    train_fe, vendor_freq_map = _engineer_features(train, vendor_freq_map=None)
    test_fe, _ = _engineer_features(test, vendor_freq_map=vendor_freq_map)

    features_train = train_fe.select(FEATURE_NAMES).to_pandas()
    y_train = train_fe["target"].to_numpy()
    y_test = test_fe["target"].to_numpy()

    # ------------------------------------------------------------------
    # Train LightGBM
    # ------------------------------------------------------------------
    pos_count = int(y_train.sum())
    neg_count = int(len(y_train) - pos_count)
    scale_pos_weight = neg_count / max(pos_count, 1)

    logger.info(
        "Training LightGBM: n_train=%d, scale_pos_weight=%.2f",
        len(train), scale_pos_weight,
    )

    model = LGBMClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        num_leaves=31,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(features_train, y_train)

    # ------------------------------------------------------------------
    # Evaluate on test set
    # ------------------------------------------------------------------
    y_prob_test = model.predict_proba(
        test_fe.select(FEATURE_NAMES).to_pandas()
    )[:, 1]
    y_pred_test = (y_prob_test >= 0.5).astype(int)

    auc_roc = float(roc_auc_score(y_test, y_prob_test))
    pr_auc = float(average_precision_score(y_test, y_prob_test))
    precision = float(precision_score(y_test, y_pred_test, zero_division=0))
    recall = float(recall_score(y_test, y_pred_test, zero_division=0))
    f1 = float(f1_score(y_test, y_pred_test, zero_division=0))

    logger.info(
        "Test metrics: AUC-ROC=%.4f | PR-AUC=%.4f | "
        "Precision=%.4f | Recall=%.4f | F1=%.4f",
        auc_roc, pr_auc, precision, recall, f1,
    )

    # Feature importance (gain)
    importance = model.feature_importances_
    feat_imp = sorted(
        zip(FEATURE_NAMES, importance.tolist(), strict=False),
        key=lambda x: x[1],
        reverse=True,
    )
    logger.info("Feature importance (gain):")
    for fname, imp in feat_imp:
        logger.info("  %-25s %.1f", fname, imp)

    # ------------------------------------------------------------------
    # Score all cases
    # ------------------------------------------------------------------
    all_fe, _ = _engineer_features(cases, vendor_freq_map=vendor_freq_map)
    y_prob_all = model.predict_proba(
        all_fe.select(FEATURE_NAMES).to_pandas()
    )[:, 1]

    # Mark which rows were in the test set (by index position in cases)
    is_test_flags = np.zeros(n_total, dtype=bool)
    is_test_flags[test_idx] = True

    result = cases.select(["case_id", "flow_type", "sla_risk"]).with_columns([
        pl.Series("sla_risk_score", y_prob_all.tolist()),
        pl.Series(
            "sla_risk_predicted",
            ["above_p75" if p >= 0.5 else "below_p75" for p in y_prob_all.tolist()],
            dtype=pl.Utf8,
        ),
        pl.Series("in_test_set", is_test_flags.tolist()),
    ])

    # ------------------------------------------------------------------
    # Persist model artifact
    # ------------------------------------------------------------------
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.SLA_MODEL_PATH, "wb") as fh:
        pickle.dump(
            {
                "model": model,
                "vendor_freq_map": vendor_freq_map,
                "feature_names": FEATURE_NAMES,
                "metrics": {
                    "auc_roc": auc_roc,
                    "pr_auc": pr_auc,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "n_train": len(train),
                    "n_test": len(test),
                    "positive_rate_overall": pos_rate,
                },
                "feature_importance": feat_imp,
            },
            fh,
        )
    logger.info("Model artifact saved: %s", config.SLA_MODEL_PATH)

    # ------------------------------------------------------------------
    # Write parquet
    # ------------------------------------------------------------------
    config.GOLD_DIR.mkdir(parents=True, exist_ok=True)
    result.write_parquet(config.GOLD_FACT_SLA_RISK, compression="zstd")
    logger.info(
        "fact_sla_risk written: %d rows, %.1f MB",
        len(result),
        config.GOLD_FACT_SLA_RISK.stat().st_size / 1e6,
    )

    return len(result)
