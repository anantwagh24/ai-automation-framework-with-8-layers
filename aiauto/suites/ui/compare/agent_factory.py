from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from .browser_controller import BrowserController


class ExcelLogger:
    """Append rows (timestamp, agent, role, content) into logs/compare_dialog.xlsx"""
    def __init__(self, filepath: str):
        from pathlib import Path
        import pandas as pd
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._pd = pd

    def append_rows(self, rows: List[Dict[str, Any]]):
        df_new = self._pd.DataFrame(rows)
        if self.filepath.exists():
            df_old = self._pd.read_excel(self.filepath)
            df = self._pd.concat([df_old, df_new], ignore_index=True)
        else:
            df = df_new
        with self._pd.ExcelWriter(self.filepath, engine="openpyxl", mode="w") as writer:
            df.to_excel(writer, index=False)

    def log_message(self, agent_name: str, role: str, content: str):
        now = datetime.now().isoformat(timespec="seconds")
        self.append_rows([{
            "timestamp": now,
            "agent": agent_name,
            "role": role,
            "content": content
        }])


class AgentFactory:
    """
    Creates:
      - TestingAgent (LLM summary optional)
      - BrowserController (Playwright)
      - ExcelLogger (artifact log)
    Also exposes helpers for typing, clicking, observing buttons, and screenshots.
    """
    def __init__(self, cfg: dict, model: str = "gpt-4o", openai_api_key: Optional[str] = None):
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key

        self.cfg = cfg
        self.model_client = OpenAIChatCompletionClient(model=model)

        self.browser = BrowserController(
            headless=bool(cfg["ui"].get("headless", False)),
            slow_mo=cfg["ui"].get("slow_mo_ms", 100),
            shots_dir=str(Path(cfg["artifacts"]["files_root"]) / "shots"),
        )
        self.excel = ExcelLogger(filepath=cfg["artifacts"]["logs_excel"])

        self.testing_agent = AssistantAgent(
            name="TestingAgent",
            model_client=self.model_client,
            system_message=(
                "You are TestingAgent. Exercise the Compare app UI and complete journeys. "
                "Be concise and action-focused in outputs."
            ),
        )

    async def aclose(self):
        await self.model_client.close()

    # ---------- Logging helpers ----------
    async def log_to_excel(self, agent_name: str, role: str, content: str):
        self.excel.log_message(agent_name, role, content)

    # ---------- UI action helpers ----------
    async def click_and_log(self, label: str, exact: bool = True) -> bool:
        ok = await self.browser.click_button_by_text(label, exact=exact)
        await self.log_to_excel("TestingAgent", "click", f"{label} -> {ok}")
        shot = await self.browser.screenshot("after-click")
        await self.log_to_excel("TestingAgent", "screenshot", shot)
        return ok

    async def type_and_log(self, message: str) -> bool:
        sent = await self.browser.try_send_message(message)
        await self.log_to_excel("TestingAgent", "say", f"'{message}' -> sent={sent}")
        shot = await self.browser.screenshot("after-say")
        await self.log_to_excel("TestingAgent", "screenshot", shot)
        return sent

    async def answer_choice(self, label: str, prefer_click: bool = False) -> str:
        """
        Answer a choice either by typing the label or clicking it.
        Returns 'typed', 'clicked', or 'failed'.
        """
        if not prefer_click:
            sent = await self.type_and_log(label)
            if sent:
                return "typed"
            ok = await self.click_and_log(label, exact=False)
            return "clicked" if ok else "failed"

        ok = await self.click_and_log(label, exact=False)
        if ok:
            return "clicked"
        sent = await self.type_and_log(label)
        return "typed" if sent else "failed"

    async def observe_current_buttons(self) -> List[str]:
        btns = await self.browser.current_buttons()
        await self.log_to_excel("TestingAgent", "buttons(current)", ", ".join(btns))
        return btns
