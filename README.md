# AI Automation Framework

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e .
python -m playwright install chromium
export OPENAI_API_KEY="sk-your-key"
aiauto ui-scenario1
