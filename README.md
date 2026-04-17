# FounderFlow AI

Memory-powered AI assistant for startup founders to track investor meetings, objections, promises, and prepare for follow-ups.

## Features

- Add investor meeting memory (notes, objections, promises)
- Prepare personalized next-meeting brief
- Generate professional follow-up email
- Local JSON memory fallback (demo-safe)
- Hindsight API-ready integration path
- Groq LLM integration for responses

## Tech Stack

- Python
- Streamlit
- Groq API
- Hindsight API (optional in MVP, local fallback included)
- python-dotenv

## Project Structure

- `app.py` - Streamlit UI and app flow
- `memory.py` - Memory management (local + Hindsight-ready)
- `llm.py` - Groq client wrapper
- `prompts.py` - Prompt templates
- `requirements.txt` - Dependencies
- `.env` - API keys

## Setup

1. Create virtual environment (recommended):

```bash
python -m venv .venv
```

2. Activate it:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Add keys in `.env`:

```env
GROQ_API_KEY=your_groq_key
HINDSIGHT_API_KEY=your_hindsight_key
```

5. Run app:

```bash
streamlit run app.py
```

## Demo Data

On first run, app preloads:

- Rahul Mehta (CAC concern, needs pitch deck)
- Priya Sharma (traction questions, needs GTM clarity)

## Hackathon Demo Flow

1. Open **Add Meeting** tab.
2. Add Rahul meeting notes:
   - Asked CAC
   - Need updated deck
3. Open **Prepare Meeting** tab and enter Rahul.
4. Show memory context + generated prep brief.
5. Open **Generate Email** tab and generate personalized follow-up.

## Notes

- If APIs are missing/unavailable, local memory fallback still works for a full demo.
- Hindsight calls are intentionally lightweight for speed in hackathon MVP.
