# aiauto/suites/ui/rag_validation/scenario2_rag_validation.py
from __future__ import annotations

from pathlib import Path
from typing import List, Dict
from datetime import datetime

from aiauto.suites.model_eval.rag_pipeline import (
    build_rag_pipeline_from_file,
    answer_with_rag,
)
from aiauto.suites.ui.compare.agent_factory import AgentFactory
from aiauto.common.metrics import semantic_agreement  # ✅ import the comparator

# ---------------------------
# Scenario 2: RAG Policy Validation
# ---------------------------
async def run_scenario2(cfg: dict) -> None:
    """
    Demonstrates RAG pipeline validation for a policy FAQ question.
    Steps:
      1. Open sample page (mock or real)
      2. Ask an LLM-like agent: “When does my policy expire?”
      3. Capture app’s response
      4. Retrieve ground truth from RAG
      5. Compare using semantic similarity
      6. Log result in HTML report
    """
    start_url = cfg["ui"].get("start_url", "https://example.com/")
    reports_dir = Path(cfg["artifacts"]["reports_dir"]).resolve(); reports_dir.mkdir(parents=True, exist_ok=True)

    rag_cfg = cfg.get("rag", {})
    ground_truth_path = rag_cfg.get("ground_truth_file", "datasets/policy_sample.txt")
    similarity_threshold = float(rag_cfg.get("similarity_threshold", 0.85))
    validation_question = rag_cfg.get("question", "When does my policy expire?")

    transcript = []
    session_id = f"scenario2-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    report_path = reports_dir / "scenario2_rag_report.html"

    # Step 1: Launch browser
    factory = AgentFactory(cfg, model="gpt-4o")
    B = factory.browser
    await B.launch()
    await B.goto(start_url)
    await B.wait_network_idle(2500)

    # Simulated / mock chat-like answer (replace with a real UI read if needed)
    ui_answer = "Your policy expires after 1 day — that’s October 25, 2025."

    transcript.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "role": "user",
        "agent": "Anant",
        "text": validation_question
    })
    transcript.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "role": "assistant",
        "agent": "Compare Bot",
        "text": ui_answer
    })

    # Step 2: Build RAG pipeline and query ground truth
    qa = build_rag_pipeline_from_file(ground_truth_path)
    rag_answer = answer_with_rag(qa, validation_question)

    # Step 3: Semantic comparison
    is_match, score = semantic_agreement(ui_answer, rag_answer, threshold=similarity_threshold)
    verdict = "PASS ✅" if is_match else "FAIL ❌"

    transcript.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "role": "judge",
        "agent": "RAG Validator",
        "text": f"{verdict} (similarity={score:.3f}, threshold={similarity_threshold})\n"
                f"Q: {validation_question}\nUI: {ui_answer}\nGT: {rag_answer}"
    })

    # Step 4: Save as HTML report
    html_rows = "".join([
        f"<tr><td>{t['timestamp']}</td><td>{t['agent']}</td>"
        f"<td style='white-space:pre-wrap'>{t['text']}</td></tr>"
        for t in transcript
    ])
    html_doc = f"""<!doctype html>
    <html><head><meta charset='utf-8'>
    <title>Scenario 2 - RAG Validation</title>
    <style>table{{border-collapse:collapse;width:100%}}
    th,td{{border:1px solid #ccc;padding:8px;vertical-align:top}}</style></head>
    <body><h1>Scenario 2 – RAG Validation</h1>
    <table><tr><th>Timestamp</th><th>Agent</th><th>Message</th></tr>{html_rows}</table></body></html>"""
    report_path.write_text(html_doc, encoding="utf-8")
    print(f"✅ Scenario 2 completed → {report_path}")

    await B.close()
    await factory.aclose()
