"""
AI Automation Framework package.

This package provides the orchestration, suites, and utilities
for running AI QA and automation tests across UI, data, model,
drift, and explainability layers.
"""

__version__ = "0.1.0"

# Optional: simple logger setup (so every module gets consistent logging)
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

# Optional: expose common entry points for external imports
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent
CONFIG_PATH = PACKAGE_ROOT / "config" / "project.yaml"

__all__ = ["__version__", "PACKAGE_ROOT", "CONFIG_PATH"]
