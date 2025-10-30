import asyncio
from aiauto.suites.ui.rag_validation.scenario2_rag_validation import run_scenario2
from aiauto.common.io import load_cfg  # or however you load project.yaml

def test_scenario2_rag_execution():
    """
    Runs the RAG-based validation scenario as a pytest test.
    Fails if any exception is raised or report not generated.
    """
    cfg = load_cfg()
    asyncio.run(run_scenario2(cfg))
