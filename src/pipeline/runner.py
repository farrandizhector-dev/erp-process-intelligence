"""Pipeline orchestrator for the ERP Process Intelligence Platform.

Manages phase execution, dependency validation, and result reporting.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from src import config

logger = logging.getLogger(__name__)

PHASE_ORDER = ["ingest", "silver", "gold", "analytics", "predict", "export"]

PHASE_INPUTS: dict[str, list[Path]] = {
    "ingest": [config.XES_FILE],
    "silver": [config.BRONZE_EVENTS, config.BRONZE_CASES],
    "gold": [config.SILVER_EVENTS, config.SILVER_CASES],
    "analytics": [config.GOLD_FACT_EVENT_LOG, config.GOLD_FACT_CASE_SUMMARY],
    "predict": [config.GOLD_FACT_CASE_SUMMARY],
    "export": [
        config.GOLD_FACT_CASE_SUMMARY,
        config.GOLD_FACT_VARIANT_STATS,
        config.GOLD_FACT_COMPLIANCE,
        config.GOLD_FACT_BOTTLENECK,
        config.GOLD_FACT_AUTOMATION,
    ],
}


@dataclass
class PhaseResult:
    """Result from executing a single pipeline phase."""

    phase: str
    status: Literal["success", "failed", "skipped"]
    duration_seconds: float
    rows_read: int = 0
    rows_written: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"[{self.status.upper()}] {self.phase} "
            f"({self.duration_seconds:.1f}s, "
            f"read={self.rows_read:,}, written={self.rows_written:,})"
        )


@dataclass
class PipelineConfig:
    """Runtime configuration for the pipeline runner."""

    xes_path: Path = config.XES_FILE
    output_dir: Path = config.DATA_DIR
    skip_validation: bool = False
    dry_run: bool = False
    log_level: str = "INFO"
    log_file: Path | None = None


class PipelineRunner:
    """Orchestrates execution of the ERP Process Intelligence pipeline.

    Args:
        config: PipelineConfig instance with runtime settings.
    """

    def __init__(self, pipeline_config: PipelineConfig) -> None:
        self.config = pipeline_config
        self.logger = logging.getLogger("pipeline.runner")

    def validate_inputs(self, phase: str) -> list[str]:
        """Check that required input files exist for a phase.

        Args:
            phase: Phase identifier (e.g., 'ingest', 'silver').

        Returns:
            List of error messages (empty if all inputs present).
        """
        errors = []
        for path in PHASE_INPUTS.get(phase, []):
            if not path.exists():
                errors.append(f"Missing input: {path}")
        return errors

    def run_phase(self, phase: str, dry_run: bool = False) -> PhaseResult:
        """Run a single pipeline phase.

        Args:
            phase: Phase identifier.
            dry_run: If True, validate inputs and print plan without executing.

        Returns:
            PhaseResult with status, duration, and row counts.
        """
        if phase not in PHASE_ORDER:
            return PhaseResult(
                phase=phase,
                status="failed",
                duration_seconds=0.0,
                errors=[f"Unknown phase '{phase}'. Valid phases: {PHASE_ORDER}"],
            )

        errors = self.validate_inputs(phase)
        if errors:
            return PhaseResult(
                phase=phase,
                status="failed",
                duration_seconds=0.0,
                errors=errors,
            )

        if dry_run:
            self.logger.info("[DRY RUN] Would execute phase: %s", phase)
            inputs = [str(p) for p in PHASE_INPUTS.get(phase, [])]
            self.logger.info("[DRY RUN] Inputs: %s", inputs)
            return PhaseResult(phase=phase, status="skipped", duration_seconds=0.0)

        self.logger.info("Starting phase: %s", phase)
        start = time.monotonic()

        try:
            result = self._dispatch_phase(phase)
            result.duration_seconds = time.monotonic() - start
            self.logger.info("Completed phase: %s", result)
            return result
        except Exception as exc:
            duration = time.monotonic() - start
            self.logger.exception("Phase %s failed: %s", phase, exc)
            return PhaseResult(
                phase=phase,
                status="failed",
                duration_seconds=duration,
                errors=[str(exc)],
            )

    def run_all(self, dry_run: bool = False) -> list[PhaseResult]:
        """Run all pipeline phases in order, stopping on failure.

        Args:
            dry_run: If True, validate and print plan without executing.

        Returns:
            List of PhaseResult, one per phase attempted.
        """
        results = []
        for phase in PHASE_ORDER:
            result = self.run_phase(phase, dry_run=dry_run)
            results.append(result)
            if result.status == "failed":
                self.logger.error(
                    "Pipeline stopped at phase '%s' due to failure. "
                    "Errors: %s",
                    phase,
                    result.errors,
                )
                break
        return results

    def _dispatch_phase(self, phase: str) -> PhaseResult:
        """Dispatch to the appropriate phase handler.

        Args:
            phase: Phase identifier.

        Returns:
            PhaseResult (duration not yet set by this method).
        """
        # Each phase handler is imported lazily to avoid loading all modules
        # when only one phase is needed.
        if phase == "ingest":
            return self._run_ingest()
        elif phase == "silver":
            return self._run_silver()
        elif phase == "gold":
            return self._run_gold()
        elif phase == "analytics":
            return self._run_analytics()
        elif phase == "predict":
            return self._run_predict()
        elif phase == "export":
            return self._run_export()
        else:
            raise ValueError(f"No handler for phase '{phase}'")

    def _run_ingest(self) -> PhaseResult:
        """Execute ingestion phase: XES → Bronze parquet."""
        from src.ingestion.bronze_writer import write_bronze
        from src.ingestion.xes_parser import parse_xes

        self.logger.info("Parsing XES file: %s", self.config.xes_path)
        events_df, cases_df = parse_xes(self.config.xes_path)

        self.logger.info(
            "Parsed %d events, %d cases", len(events_df), len(cases_df)
        )

        write_bronze(events_df, cases_df, skip_validation=self.config.skip_validation)

        return PhaseResult(
            phase="ingest",
            status="success",
            duration_seconds=0.0,
            rows_read=0,
            rows_written=len(events_df) + len(cases_df),
        )

    def _run_silver(self) -> PhaseResult:
        """Execute silver layer transformation."""
        from src.transformation.silver_builder import build_silver

        rows_read, rows_written = build_silver(
            skip_validation=self.config.skip_validation
        )
        return PhaseResult(
            phase="silver",
            status="success",
            duration_seconds=0.0,
            rows_read=rows_read,
            rows_written=rows_written,
        )

    def _run_gold(self) -> PhaseResult:
        """Execute gold layer mart building."""
        from src.gold.mart_builder import build_gold_marts

        rows_written = build_gold_marts(skip_validation=self.config.skip_validation)
        return PhaseResult(
            phase="gold",
            status="success",
            duration_seconds=0.0,
            rows_written=rows_written,
        )

    def _run_analytics(self) -> PhaseResult:
        """Execute analytics computations."""
        from src.gold.mart_builder import run_analytics

        rows_written = run_analytics()
        return PhaseResult(
            phase="analytics",
            status="success",
            duration_seconds=0.0,
            rows_written=rows_written,
        )

    def _run_predict(self) -> PhaseResult:
        """Execute predictive layer (SLA risk model)."""
        try:
            from src.analytics.predictive import build_sla_risk_model

            rows_written = build_sla_risk_model()
            return PhaseResult(
                phase="predict",
                status="success",
                duration_seconds=0.0,
                rows_written=rows_written,
            )
        except ImportError:
            self.logger.warning("Predictive module not yet built — skipping predict phase.")
            return PhaseResult(phase="predict", status="skipped", duration_seconds=0.0)

    def _run_export(self) -> PhaseResult:
        """Execute frontend JSON export."""
        from scripts.export_for_frontend import export_all

        files_written = export_all()
        return PhaseResult(
            phase="export",
            status="success",
            duration_seconds=0.0,
            rows_written=files_written,
        )
