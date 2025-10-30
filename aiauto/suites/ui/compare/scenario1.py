# aiauto/suites/ui/compare/scenario1.py
from __future__ import annotations
import io
import os
import re
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple


import pandas as pd

from .agent_factory import AgentFactory

# =========================
# Constants
# =========================
SCENARIO_TITLE = "Scenario 1 – Direct Entry To Comparison"
# CSV/XLSX with two columns: Speaker, Message
EXCEL_TRANSCRIPT = "files/chat_conversation.csv"

# =========================
# Transcript Loading (robust)
# =========================
def _strip_outer_quotes_from_lines(raw: str) -> str:
    """
    Some tools export CSV as lines fully wrapped in quotes, e.g.:
        "Speaker,Message"
        "Compare,Welcome ..."
    This removes the outer quotes safely and unescapes doubled quotes.
    """
    lines = raw.splitlines()
    if not lines:
        return raw
    header = lines[0].strip()
    if header.startswith('"') and header.endswith('"') and "," in header:
        out = []
        for ln in lines:
            s = ln.strip()
            if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
                s = s[1:-1]
                s = s.replace('""', '"')
            out.append(s)
        return "\n".join(out)
    return raw


def _load_transcript_any(path_str: str) -> pd.DataFrame:
    """
    Loads transcript from CSV/XLS/XLSX robustly and normalizes headers to 'Speaker' & 'Message'.
    """
    p = Path(path_str)
    if not p.exists():
        raise FileNotFoundError(f"Transcript not found: {p.resolve()}")

    ext = p.suffix.lower()
    if ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        df = pd.read_excel(p, engine="openpyxl")
    elif ext == ".xls":
        df = pd.read_excel(p, engine="xlrd")
    elif ext == ".xlsb":
        df = pd.read_excel(p, engine="pyxlsb")
    elif ext == ".csv":
        raw = p.read_text(encoding="utf-8", errors="replace")
        raw = raw.lstrip("\ufeff")  # strip BOM if present
        raw = _strip_outer_quotes_from_lines(raw)

        # Try to sniff delimiter on the (now cleaned) header
        try:
            sniff = csv.Sniffer().sniff(raw.splitlines()[0])
            sep = sniff.delimiter
        except Exception:
            sep = ","

        # Try Pandas parse with sep; fallback to inference
        try:
            df = pd.read_csv(io.StringIO(raw), sep=sep)
        except Exception:
            df = pd.read_csv(io.StringIO(raw), sep=None, engine="python")
    else:
        raise ValueError(f"Unsupported transcript extension '{ext}'. Use .xlsx/.xls/.xlsb/.csv")

    # Normalize headers and keep the 2 required columns
    df.columns = [str(c).strip() for c in df.columns]
    lower = {c.lower(): c for c in df.columns}
    if "speaker" not in lower or "message" not in lower:
        raise ValueError(
            f"Expected columns 'Speaker' and 'Message' in {path_str}. Found: {list(df.columns)}"
        )

    df = df[[lower["speaker"], lower["message"]]].rename(
        columns={lower["speaker"]: "Speaker", lower["message"]: "Message"}
    )
    return df


def build_steps_from_excel(path: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Reads a transcript with columns: Speaker, Message
    Returns:
      - steps: only Anant's rows converted to actions (click/text)
      - context: all rows for the HTML report (assistant/user)
    """
    df = _load_transcript_any(path)

    if os.getenv("AIQA_DEBUG") == "1":
        print("DEBUG transcript columns:", list(df.columns))
        try:
            print(df.head().to_string(index=False))
        except Exception:
            pass

    steps: List[Dict[str, str]] = []
    context: List[Dict[str, str]] = []

    # Map common phrases to UI button labels
    click_map = [
        (r"\bLive in it\b", "Live in it"),
        (r"\bRent it out\b", "Rent it out"),
        (r"\b6\+\s*months\b", "6+ months away"),
        (r"\b3-6\s*months\b", "3-6 months away"),
        (r"\bless than 3 months\b", "Less than 3 months"),
        (r"\balready ended\b", "It's already ended"),
        (r"\bCheck here\b", "Check here"),
    ]

    for _, row in df.iterrows():
        who = str(row.get("Speaker", "")).strip()
        msg = str(row.get("Message", "")).strip()

        # For report: Compare -> assistant; others -> user
        context.append({
            "role": "assistant" if who.lower().startswith("compare") else "user",
            "agent": who or "Unknown",
            "text": msg,
        })

        # Test step: only Anant's turns become actions
        if who.lower() == "anant" and msg:
            matched = False
            for patt, label in click_map:
                if re.search(patt, msg, flags=re.I):
                    steps.append({"action": "click", "label": label})
                    matched = True
                    break
            if not matched:
                steps.append({"role": "user", "text": msg})

    return steps, context

# =========================
# HTML Report
# =========================
def _escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_html_report(transcript: List[Dict[str, str]], out_path: Path, session_id: str, title: str) -> None:
    """
    Simple HTML report. Shows time, who, message/action, and inline screenshots.
    """
    rows_html = []
    for turn in transcript:
        ts = turn.get("timestamp", "")
        who = turn.get("agent", turn.get("role", ""))
        text = _escape_html(turn.get("text", turn.get("content", "")))
        shot = turn.get("screenshot")
        row = [f"<tr><td>{ts}</td><td>{_escape_html(who)}</td><td style='white-space:pre-wrap'>{text}"]
        if shot:
            row.append(
                f"<div style='margin-top:6px'><img src='{shot}' alt='screenshot' "
                f"style='max-width:100%;border:1px solid #ddd;border-radius:6px'/></div>"
            )
        row.append("</td></tr>")
        rows_html.append("".join(row))

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} (Session {session_id})</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 body {{ font-family: -apple-system, system-ui, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 24px; }}
 table {{ border-collapse: collapse; width: 100%; }}
 th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
 th {{ background: #f7f7f7; text-align: left; }}
</style>
</head>
<body>
<h1>{title}</h1>
<table>
  <thead><tr><th>Timestamp</th><th>Who</th><th>Message / Action</th></tr></thead>
  <tbody>
    {''.join(rows_html)}
  </tbody>
</table>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")

# =========================
# Prompt for optional LLM summary
# =========================
SCENARIO1_TESTING_PROMPT = """
You are TestingAgent validating Scenario 1 – Direct Entry To Comparison in the Compare app.

Goal
- Complete the remortgage comparison journey end-to-end, based on the provided transcript.

Rules
- Prefer typing the exact choice labels (e.g., "3-6 months away", "Live in it", "Check here").
- If typing is ineffective, clicking those options is acceptable.
- Keep answers short and factual; no fluff.
- After each step, confirm the UI progressed (new question, results table, or product details).

Output
- Bullet list of the actions taken (Typed or Clicked), any assumptions, and the end state.
"""

# =========================
# Helpers
# =========================
async def _safe_screenshot(browser_ctrl, name_prefix: str) -> str:
    """
    Calls BrowserController.screenshot if available, otherwise tries Playwright page.screenshot.
    Returns path or empty string on failure.
    """
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        if hasattr(browser_ctrl, "screenshot"):
            return await browser_ctrl.screenshot(name_prefix)
    except Exception:
        pass

    # Fallback path
    try:
        shots_dir = Path("files/shots"); shots_dir.mkdir(parents=True, exist_ok=True)
        out = shots_dir / f"{name_prefix}-{ts}.png"
        if getattr(browser_ctrl, "page", None):
            await browser_ctrl.page.screenshot(path=str(out))
            return str(out)
    except Exception:
        return ""
    return ""

# =========================
# Scenario Runner
# =========================
async def run_scenario1(cfg: dict) -> None:
    """
    Scenario 1 – Direct Entry To Comparison:
      - Opens the app
      - Replays steps from transcript (Anant rows -> clicks or free text)
      - Uses a progression policy (progress buttons + common choices)
      - Logs to Excel and generates an HTML report
    """
    start_url = cfg["ui"]["start_url"]
    reports_dir = Path(cfg["artifacts"]["reports_dir"]).resolve(); reports_dir.mkdir(parents=True, exist_ok=True)
    files_root = Path(cfg["artifacts"]["files_root"]).resolve(); files_root.mkdir(parents=True, exist_ok=True)
    logs_excel = cfg["artifacts"]["logs_excel"]

    transcript: List[Dict[str, str]] = []
    manual_convo, context_transcript = build_steps_from_excel(EXCEL_TRANSCRIPT)

    factory = AgentFactory(cfg, model="gpt-4o")
    B = factory.browser

    session_id = f"scenario1-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    report_path = reports_dir / "scenario1_report.html"

    # Add opening context (Compare Agent prompts + Anant replies) to the report
    now_iso = datetime.now().isoformat(timespec="seconds")
    for t in context_transcript:
        transcript.append({"timestamp": now_iso, **t})

    # --- Open the app and settle
    await B.launch()
    await B.goto(start_url)
    await B.wait_network_idle(3500)
    await B.settle(600)

    shot = await _safe_screenshot(B, "after-open")
    transcript.append({"timestamp": datetime.now().isoformat(timespec="seconds"),
                       "role": "action", "agent": "TestingAgent",
                       "text": "Opened app.", "screenshot": shot})

    # Cookie / consent banners (best-effort)
    for label in ["Accept all cookies", "Accept", "I agree", "Got it", "Close"]:
        try:
            ok = await B.click_button_by_text(label, exact=False)
        except Exception:
            ok = False
        if ok:
            shot = await _safe_screenshot(B, "after-cookie")
            transcript.append({"timestamp": datetime.now().isoformat(timespec="seconds"),
                               "role": "action", "agent": "TestingAgent",
                               "text": f"Clicked consent: {label}", "screenshot": shot})
            break

    # -------- Context-aware runner --------
    CHOICE_PREFERENCES = {"term_end": None, "occupancy": None}
    for t in context_transcript:
        txt = t.get("text", "").lower()
        if "live in it" in txt:
            CHOICE_PREFERENCES["occupancy"] = "Live in it"
        elif "rent it out" in txt:
            CHOICE_PREFERENCES["occupancy"] = "Rent it out"
        if "6+ months" in txt:
            CHOICE_PREFERENCES["term_end"] = "6+ months away"
        elif "3-6 months" in txt or "3 – 6 months" in txt or "3–6 months" in txt:
            CHOICE_PREFERENCES["term_end"] = "3-6 months away"
        elif "less than 3 months" in txt:
            CHOICE_PREFERENCES["term_end"] = "Less than 3 months"
        elif "already ended" in txt:
            CHOICE_PREFERENCES["term_end"] = "It's already ended"

    PROGRESS_BUTTONS = [
        "Compare live mortgage deals",
        "Get an expert recommendation",
        "Continue",
        "Next",
        "Compare deals",
        "Start comparison",
        "Proceed",
        "OK",
    ]

    pending_steps = list(manual_convo)

    def _pop_next_free_text():
        for i, s in enumerate(pending_steps):
            if "text" in s and not s.get("action"):
                return pending_steps.pop(i)
        return None

    def _pop_matching_click(visible_buttons):
        for i, s in enumerate(pending_steps):
            if s.get("action") == "click":
                lab = s.get("label", "")
                if any(lab.lower() in b.lower() for b in visible_buttons):
                    return pending_steps.pop(i)
        return None

    answered = {"term_end": False, "occupancy": False}

    # Main loop with hard cap to avoid infinite loops
    for _ in range(80):
        await B.wait_network_idle(4000)
        await B.settle(450)

        # The factory helper logs visible buttons into Excel and returns bottom-cluster labels
        visible = await factory.observe_current_buttons()
        ts = datetime.now().isoformat(timespec="seconds")

        term_end_set = {"6+ months away", "3-6 months away", "Less than 3 months", "It's already ended"}
        occupancy_set = {"Live in it", "Rent it out"}

        # 0) Progress buttons
        next_progress = None
        for pbtn in PROGRESS_BUTTONS:
            if any(pbtn.lower() in b.lower() for b in visible):
                # prefer specific main CTA if present
                next_progress = "Compare live mortgage deals" if any(
                    "compare live mortgage deals" in b.lower() for b in visible
                ) else pbtn
                break
        if next_progress:
            how = await factory.answer_choice(next_progress, prefer_click=False)
            shot = await _safe_screenshot(B, "after-progress")
            transcript.append({"timestamp": ts, "role": "action", "agent": "TestingAgent",
                               "text": f"Progressed via '{next_progress}' using {how}",
                               "screenshot": shot})
            continue

        # 1) Term end (answer once)
        if not answered["term_end"] and len(set(visible) & term_end_set) >= 2:
            choice = CHOICE_PREFERENCES.get("term_end") or "3-6 months away"
            how = await factory.answer_choice(choice, prefer_click=False)
            shot = await _safe_screenshot(B, "after-term-end-answer")
            transcript.append({"timestamp": ts, "role": "action", "agent": "TestingAgent",
                               "text": f"Answered 'term end' -> {choice} via {how}",
                               "screenshot": shot})
            answered["term_end"] = True
            continue

        # 2) Occupancy (answer once)
        if not answered["occupancy"] and len(set(visible) & occupancy_set) >= 1:
            choice = CHOICE_PREFERENCES.get("occupancy") or "Live in it"
            how = await factory.answer_choice(choice, prefer_click=False)
            shot = await _safe_screenshot(B, "after-occupancy-answer")
            transcript.append({"timestamp": ts, "role": "action", "agent": "TestingAgent",
                               "text": f"Answered 'occupancy' -> {choice} via {how}",
                               "screenshot": shot})
            answered["occupancy"] = True
            continue

        # 3) Product results (“Check here”)
        if any("check here" in b.lower() for b in visible):
            how = await factory.answer_choice("Check here", prefer_click=False)
            shot = await _safe_screenshot(B, "after-check-here")
            transcript.append({"timestamp": ts, "role": "action", "agent": "TestingAgent",
                               "text": f"Chose product via {how}",
                               "screenshot": shot})
            continue

        # 4) Explicit click from transcript matching current cluster (typed first)
        next_click = _pop_matching_click(visible)
        if next_click:
            how = await factory.answer_choice(next_click["label"], prefer_click=False)
            shot = await _safe_screenshot(B, "after-explicit-choice")
            transcript.append({"timestamp": ts, "role": "action", "agent": "TestingAgent",
                               "text": f"Matched transcript choice '{next_click['label']}' via {how}",
                               "screenshot": shot})
            continue

        # 5) Next free text from transcript
        nxt = _pop_next_free_text()
        if nxt:
            sent = await factory.type_and_log(nxt["text"])
            shot = await _safe_screenshot(B, "after-free-text")
            transcript.append({"timestamp": ts, "role": "user", "agent": "You",
                               "text": nxt["text"], "screenshot": shot})
            continue

        # in scenario1.py main loop, before “idle-no-action” break:
        for _ in range(3):
            await B.scroll_down(900)
            visible = await factory.observe_current_buttons()
            if visible:
                break

        # 6) Nothing to do
        shot = await _safe_screenshot(B, "idle-no-action")
        transcript.append({"timestamp": ts, "role": "info", "agent": "TestingAgent",
                           "text": "No matching buttons or text left; pausing.",
                           "screenshot": shot})
        break

    # Optional LLM summary (skipped if AIQA_SKIP_LLM=1)
    summary_text = "LLM summary skipped."
    if os.getenv("AIQA_SKIP_LLM") != "1":
        try:
            summary_msg = await factory.testing_agent.run(SCENARIO1_TESTING_PROMPT)
            summary_text = getattr(summary_msg, "content", str(summary_msg))
        except Exception as e:
            summary_text = f"Summary failed: {e}"

    await factory.log_to_excel("TestingAgent", "summary", summary_text)
    transcript.append({"timestamp": datetime.now().isoformat(timespec="seconds"),
                       "role": "assistant", "agent": "TestingAgent", "text": summary_text})

    # HTML report
    render_html_report(transcript=transcript, out_path=report_path, session_id=session_id, title=SCENARIO_TITLE)

    # Close
    await B.close()
    await factory.aclose()
    print(f"HTML report: {report_path}")
