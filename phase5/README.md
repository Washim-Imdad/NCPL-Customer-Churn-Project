# Phase 5: GenAI Streamlit App

## Architecture (accuracy-first)

1. **Verified data engine** — every answer is computed from Phase 1 CSV, Phase 3 ML predictions, and Phase 2 combined SQL query results (`output/phase2/query_results/Combined Query Results.csv`).
2. **Google Gemini** — when `GOOGLE_API_KEY` is set, Gemini rewrites the verified facts into natural language. It never invents numbers.
3. **No Ollama/Llama** — local LLMs were removed because they caused inaccurate answers.

## Run the app

```powershell
cd "C:\Users\Washim\Desktop\Project 1 NCPL"
& "venv\Scripts\python.exe" -m streamlit run phase5\app.py
```

## Install dependencies

```powershell
pip install streamlit python-dotenv langchain langchain-google-genai google-generativeai pandas matplotlib
```

Optional OpenAI fallback:

```powershell
pip install langchain-openai
```

## LLM options

| Mode | Setup |
|------|--------|
| **Verified data (default)** | No API key — direct answers from CSV/SQL exports |
| **Gemini + verified data** | `GOOGLE_API_KEY` in `phase5/.env` |
| **OpenAI + verified data** | `OPENAI_API_KEY` in `phase5/.env` (fallback) |

Get a Gemini API key: https://aistudio.google.com/apikey

## Combined query results

Place or update `output/phase2/query_results/Combined Query Results.csv` — the app parses all 23 Phase 2 query blocks automatically.

## Files

| File | Role |
|------|------|
| `app.py` | Streamlit UI |
| `agent.py` | Gemini synthesis over verified facts |
| `analytics_tools.py` | Pandas analytics + intent routing |
| `query_insights.py` | Phase 2 combined CSV parser |
