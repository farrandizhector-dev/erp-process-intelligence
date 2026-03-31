#!/usr/bin/env python3
"""CLI entry point for the ERP Process Intelligence Pipeline.

Usage:
  python scripts/run_pipeline.py [OPTIONS]

Options:
  --phase PHASE       Run specific phase: ingest, silver, gold, analytics, predict, export
  --all               Run full pipeline (ingest → silver → gold → analytics → predict → export)
  --dry-run           Validate inputs and print plan without executing
  --skip-validation   Skip Pandera schema validation (faster, for dev)
  --log-level LEVEL   Set logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
  --log-file FILE     Write logs to file in addition to stdout
  --xes-path PATH     Override default XES file path
  --output-dir DIR    Override default output directory

Examples:
  python scripts/run_pipeline.py --phase ingest
  python scripts/run_pipeline.py --phase silver --dry-run
  python scripts/run_pipeline.py --all --log-file pipeline.log
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import config
from src.pipeline.runner import PipelineConfig, PipelineRunner


def setup_logging(level: str, log_file: Path | None) -> None:
    """Configure root logger with console and optional file handler.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to write logs to.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="ERP Process Intelligence Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--phase",
        choices=["ingest", "silver", "gold", "analytics", "predict", "export"],
        help="Run a specific pipeline phase.",
    )
    mode.add_argument(
        "--all",
        action="store_true",
        help="Run the full pipeline.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print plan without executing.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip Pandera schema validation (faster for development).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO).",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Write logs to this file in addition to stdout.",
    )
    parser.add_argument(
        "--xes-path",
        type=Path,
        default=config.XES_FILE,
        help=f"Override XES file path (default: {config.XES_FILE}).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=config.DATA_DIR,
        help=f"Override output data directory (default: {config.DATA_DIR}).",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point. Returns exit code (0 = success, 1 = failure)."""
    args = parse_args()
    setup_logging(args.log_level, args.log_file)

    logger = logging.getLogger("pipeline.cli")
    logger.info("ERP Process Intelligence Pipeline — starting")

    pipeline_config = PipelineConfig(
        xes_path=args.xes_path,
        output_dir=args.output_dir,
        skip_validation=args.skip_validation,
        dry_run=args.dry_run,
        log_level=args.log_level,
        log_file=args.log_file,
    )

    runner = PipelineRunner(pipeline_config)

    if args.all:
        logger.info("Running full pipeline (all phases)")
        results = runner.run_all(dry_run=args.dry_run)
    else:
        logger.info("Running single phase: %s", args.phase)
        results = [runner.run_phase(args.phase, dry_run=args.dry_run)]

    # Print summary
    print("\n--- Pipeline Summary ---")
    all_success = True
    for result in results:
        print(f"  {result}")
        if result.status == "failed":
            all_success = False
            for err in result.errors:
                print(f"    ERROR: {err}")
        for warn in result.warnings:
            print(f"    WARNING: {warn}")

    if all_success:
        logger.info("Pipeline completed successfully.")
        return 0
    else:
        logger.error("Pipeline completed with failures.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
