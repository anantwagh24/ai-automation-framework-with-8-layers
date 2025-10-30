# aiauto/cli.py
from __future__ import annotations
import asyncio
from pathlib import Path
import typer
import yaml

app = typer.Typer(help="AI Automation Framework CLI")

def load_cfg() -> dict:
    cfg_path = Path(__file__).parent / "config" / "project.yaml"
    return yaml.safe_load(cfg_path.read_text())

@app.command("ui-scenario1")
def cmd_ui_scenario1():
    # ⬇️ lazy import avoids circulars / heavy deps at startup
    from aiauto.suites.ui.compare.scenario1 import run_scenario1
    cfg = load_cfg()
    asyncio.run(run_scenario1(cfg))

@app.command("ui-scenario2")
def cmd_ui_scenario2():
    # ⬇️ lazy import avoids circulars
    from aiauto.suites.ui.rag_validation.scenario2_rag_validation import run_scenario2
    cfg = load_cfg()
    asyncio.run(run_scenario2(cfg))

@app.command("data-validate")
def cmd_data_validate():
    from aiauto.suites.data_validation.run_ge import run_ge_suite
    res = run_ge_suite("aiauto/config/project.yaml", suite="eval_dataset_suite")
    typer.echo(f"GE suite success: {res.success}")

@app.command("drift-check")
def cmd_drift_check():
    from aiauto.suites.drift.run_evidently import compute_drift
    report = compute_drift(ref_path="datasets/train.parquet", cur_path="datasets/eval.parquet")
    typer.echo(f"Drift report: {report}")

@app.command("model-eval")
def cmd_model_eval(
    preds: str = typer.Option("datasets/preds.csv", help="CSV with columns: y_true,y_pred"),
):
    from aiauto.suites.model_eval.evaluate import evaluate_predictions
    metrics = evaluate_predictions(preds)
    typer.echo(f"Model metrics: {metrics}")

@app.command("explain-run")
def cmd_explain():
    from aiauto.suites.explain.run_shap import run_shap_explain
    typer.echo("Running SHAP explain (stub)...")
    run_shap_explain()

@app.command("contract-test")
def cmd_contract():
    from aiauto.suites.contract.api_contract_tests import run_contracts
    ok = run_contracts()
    typer.echo(f"Contract tests ok: {ok}")

def main():
    app()

if __name__ == "__main__":
    main()
