import os
import pytest
import asyncio
from pathlib import Path
import yaml
from aiauto.suites.ui.compare.scenario1 import run_scenario1

def load_cfg():
    p = Path(__file__).parent.parent / "aiauto" / "config" / "project.yaml"
    return yaml.safe_load(p.read_text())

@pytest.mark.asyncio
async def test_ui_scenario1_generates_report(tmp_path):
    # Skip if Playwright not installed or OPENAI_API_KEY missing (UI startup doesn't need the key, but keep check if you add LLM later)
    try:
        import playwright  # noqa
    except Exception:
        pytest.skip("Playwright not installed")
    cfg = load_cfg()
    # run with temp artifact dirs
    cfg["artifacts"]["reports_dir"] = str(tmp_path / "reports")
    cfg["artifacts"]["files_root"] = str(tmp_path / "files")
    Path(cfg["artifacts"]["reports_dir"]).mkdir(parents=True, exist_ok=True)
    Path(cfg["artifacts"]["files_root"]).mkdir(parents=True, exist_ok=True)
    await run_scenario1(cfg)
    assert (Path(cfg["artifacts"]["reports_dir"]) / "scenario1_report.html").exists()
