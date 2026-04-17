# FounderFlow AI

Memory-powered AI assistant for startup founders to track investor meetings, objections, promises, and prepare for follow-ups.

## Features

- Add investor meeting memory (notes, objections, promises)
- Prepare personalized next-meeting brief
- Generate professional follow-up email
- Local JSON memory fallback (demo-safe)
- Hindsight cloud sync (POST on save, GET merge for Overview / chat / prep)
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
- `Dockerfile` / `render.yaml` - deploy online
- `runtime.txt` - Python version hint for Streamlit Cloud
- `.env` - API keys (local only; never commit)

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
# Default host is Hindsight Cloud (Vectorize). Optional overrides:
# HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
# HINDSIGHT_BANK_ID=founderflow
```

### Hindsight (Hindsight Cloud / Vectorize)

The default API host is **[`https://api.hindsight.vectorize.io`](https://docs.hindsight.vectorize.io/api-integration)** (see [API integration](https://docs.hindsight.vectorize.io/api-integration)). The app uses your **[memory bank](https://hindsight.vectorize.io/developer/api/memory-banks)** id (**`HINDSIGHT_BANK_ID`**, default `founderflow`) for **retain** (save), **list** (merge into Overview/chat), and **recall** (investor search).

1. Put **`HINDSIGHT_API_KEY`** in `.env` (or Streamlit **Secrets** online) and restart.
2. **Save Memory** writes `memory_store.json` locally and **retains** the meeting JSON in your bank (`POST .../v1/default/banks/{bank_id}/memories`).
3. **Overview**, **Memory chat**, and investor flows **merge** listed cloud rows with local rows (deduped, ~45s cache). Sidebar **Pull Hindsight → local file** appends cloud-only rows into `memory_store.json`.
4. Legacy **`https://api.hindsight.ai/v1/memories`** is still supported if you set **`HINDSIGHT_BASE_URL`** to that exact style of URL.

5. Run locally:

```bash
streamlit run app.py
```

## Deploy online

Repo root must contain **`app.py`**, **`requirements.txt`**, and **`.streamlit/config.toml`** (this project already does). **`memory_store.json`** is gitignored; on free hosts the filesystem is often **ephemeral**, so use **Hindsight** (or **Pull Hindsight → local file** before restarts) if you need data to survive.

### Streamlit Community Cloud (quickest)

1. Push the `founderflow` app folder to GitHub (**public** repo for the free tier).
2. Open [Streamlit Community Cloud](https://share.streamlit.io/), sign in with GitHub → **New app**.
3. Select the repo, branch, and set **Main file path** to **`app.py`**.
4. Under **Advanced settings** → **Secrets**, add:

   ```toml
   GROQ_API_KEY = "your_groq_key"
   HINDSIGHT_API_KEY = "your_hindsight_key"
   # HINDSIGHT_BASE_URL = "https://api.hindsight.vectorize.io"
   # HINDSIGHT_BANK_ID = "founderflow"
   ```

   The app copies these into the process environment on startup.

5. **Deploy**. Share the generated `*.streamlit.app` URL.

### Render / Fly.io / Railway (Docker)

1. Use the included **`Dockerfile`** (listens on **8501**, binds **0.0.0.0**).
2. Create a **Web** service, choose **Docker**, root = this folder.
3. Set environment variables: **`GROQ_API_KEY`**, **`HINDSIGHT_API_KEY`**, and optionally **`HINDSIGHT_BASE_URL`** / **`HINDSIGHT_BANK_ID`**.
4. Optional: import **`render.yaml`** on Render as a blueprint.

## Demo Data

The local store starts **empty** until you use **Load demo data** or add meetings. Demo rows include Rahul Mehta, Priya Sharma, and Arjun Kapoor.

## Hackathon Demo Flow

1. Open **Add meeting** from the sidebar.
2. Add Rahul meeting notes:
   - Asked CAC
   - Need updated deck
3. Open **Prepare Meeting** tab and enter Rahul.
4. Show memory context + generated prep brief.
5. Open **Generate Email** tab and generate personalized follow-up.

## Notes

- If APIs are missing/unavailable, local memory fallback still works for a full demo.
- Hindsight calls are intentionally lightweight for speed in hackathon MVP.
