"""Runtime orchestration for threat generation.

This module should stay UI-agnostic: no Tkinter imports, no widget code.
The GUI (or a future CLI) calls `run_threat_modeling()` and optionally
provides a `log_callback` to receive log lines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ai_client import AIClientOptions, generate_threats
from utils import load_json, update_threats_in_file
from validator import ThreatValidator, ValidationResult

# Project paths (used for logs + default assets/schema locations).
# If you later package the app, consider switching these to importlib.resources.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
LOGS_DIR = PROJECT_ROOT / "logs"

_LOGGER_NAME = "threat_modeling"


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Configuration for a single threat-modeling run."""

    llm_model: str
    schema_path: Path
    model_path: Path
    model_file_label: str
    log_level: int = logging.INFO
    ai_options: Optional[AIClientOptions] = None


class CallbackLogHandler(logging.Handler):
    """Forward formatted log records to a callback."""

    def __init__(self, callback: Callable[[str], None]) -> None:
        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._callback(self.format(record))
        except Exception:
            self.handleError(record)


def setup_logging(
    *,
    log_level: int,
    log_callback: Optional[Callable[[str], None]] = None,
) -> logging.Logger:
    """Create a fresh logger for a run.

    - Always logs to a timestamped file under ./logs
    - If `log_callback` is provided, also forwards log lines there
    - If no callback is provided, logs to stderr as well
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"threat_modeling_{timestamp}.log"

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)  # keep everything; handler levels decide output
    logger.propagate = False
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    logger.addHandler(file_handler)

    message_only = logging.Formatter("%(message)s")

    if log_callback is not None:
        callback_handler = CallbackLogHandler(log_callback)
        callback_handler.setLevel(log_level)
        callback_handler.setFormatter(message_only)
        logger.addHandler(callback_handler)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(message_only)
        logger.addHandler(console_handler)

    return logger


def run_threat_modeling(
    config: RuntimeConfig,
    *,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Optional[ValidationResult]:
    """Run threat generation, write results back to the model file, validate output."""
    logger = setup_logging(log_level=config.log_level, log_callback=log_callback)
    ai_options = config.ai_options or AIClientOptions()

    logger.info("=" * 60)
    logger.info("STARTING AI-POWERED THREAT MODELING TOOL")
    logger.info("=" * 60)
    logger.info(
        "Configuration: model=%s, schema=%s, model_file=%s",
        config.llm_model,
        config.schema_path.name,
        config.model_path.name,
    )

    if not config.schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {config.schema_path}")
    if not config.model_path.exists():
        raise FileNotFoundError(f"Threat model file not found: {config.model_path}")

    logger.info("Loading files...")
    schema = load_json(config.schema_path)
    model = load_json(config.model_path)

    logger.info("Generating threats...")
    threats_data = generate_threats(schema, model, config.llm_model, ai_options)

    logger.debug("AI Response Details:")
    for elem_id, threats in threats_data.items():
        logger.debug("  Element %s: %s threats", elem_id, len(threats))
        for i, threat in enumerate(threats, start=1):
            logger.debug(
                "    Threat %s: %s (%s) - %s",
                i,
                threat.get("title", "No title"),
                threat.get("severity", "Unknown severity"),
                threat.get("status", "Unknown status"),
            )

    update_threats_in_file(config.model_path, threats_data)
    logger.info("Updated model saved to %s", config.model_path)

    validation_result: Optional[ValidationResult] = None
    try:
        logger.info("Validating AI response...")
        validator = ThreatValidator()
        ai_response_format = [{"id": elem_id, "threats": threats} for elem_id, threats in threats_data.items()]
        validation_result = validator.validate_ai_response(
            model,
            ai_response_format,
            config.model_file_label,
        )
        validator.print_summary(logger, validation_result)
    except Exception as exc:
        logger.error("Validation error: %s", exc)

    logger.info("=" * 60)
    logger.info("THREAT MODELING PROCESS COMPLETED")
    logger.info("=" * 60)
    logger.info("\n")
    logger.info("\n")
    return validation_result
