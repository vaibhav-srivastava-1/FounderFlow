"""Central dark professional theme for FounderFlow (Streamlit custom CSS)."""

FF_GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&"
    "family=JetBrains+Mono:wght@400;500&display=swap"
)

DARK_PRO_THEME_CSS = """
:root {
  --bg-deep: #050810;
  --bg-app: #0a0e14;
  --bg-elevated: #0f141c;
  --bg-surface: #121a24;
  --border-subtle: rgba(148, 163, 184, 0.1);
  --border-strong: rgba(34, 211, 238, 0.28);
  --text-primary: #e8f0f7;
  --text-secondary: #94a8bc;
  --text-muted: #6b7f95;
  /* Neon cyan primary (adaptive / “codesight” panel energy, still FounderFlow) */
  --accent: #22d3ee;
  --accent-hover: #67e8f9;
  --accent-glow: rgba(34, 211, 238, 0.45);
  --cyan-glow: rgba(34, 211, 238, 0.18);
  --signal-warn: #fbbf24;
  --signal-danger: #fb7185;
  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 18px;
}

@keyframes ff-rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
  color: var(--text-primary);
}

.stApp {
  font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, sans-serif !important;
  background: var(--bg-app) !important;
  background-image:
    radial-gradient(ellipse 120% 80% at 50% -25%, rgba(34, 211, 238, 0.09), transparent 55%),
    radial-gradient(ellipse 70% 45% at 100% 40%, rgba(251, 113, 133, 0.04), transparent 50%) !important;
}

.stApp::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background: linear-gradient(180deg, rgba(7, 10, 15, 0.4) 0%, transparent 35%, rgba(7, 10, 15, 0.25) 100%);
}

section[data-testid="stMain"] > div {
  position: relative;
  z-index: 1;
  background: transparent !important;
}

.main .block-container {
  padding-top: 1.25rem;
  padding-bottom: 2.75rem;
  max-width: 1180px;
}

h1, h2, h3, h4, h5, h6 {
  font-family: "Inter", system-ui, sans-serif !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em;
  color: var(--text-primary) !important;
}

p, label, span, li {
  color: var(--text-primary);
}

.stCaption, [data-testid="stCaptionContainer"] {
  color: var(--text-muted) !important;
}

.stTextInput input, .stTextArea textarea, .stChatInput textarea {
  cursor: text !important;
}
.stButton > button, .stLinkButton > a, [data-baseweb="tab"], summary {
  cursor: pointer !important;
}

/* Top band */
.ff-pro-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.5rem 0 1rem 0;
  margin-bottom: 0.15rem;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted) !important;
}

/* Hero */
.ff-hero-shell {
  position: relative;
  border-radius: var(--radius-lg);
  padding: 1.6rem 1.75rem;
  margin: 0 0 1.35rem 0;
  overflow: hidden;
  background: var(--bg-surface);
  border: 1px solid var(--border-strong);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
  animation: ff-rise 0.45s ease-out both;
}
.ff-hero-grid {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  position: relative;
  z-index: 1;
}
.ff-hero-title {
  font-size: clamp(1.65rem, 3.5vw, 2.2rem);
  font-weight: 700;
  margin: 0 0 0.4rem 0;
  line-height: 1.15;
  color: var(--text-primary) !important;
  letter-spacing: -0.03em;
}
.app-subtitle {
  color: var(--text-secondary) !important;
  margin: 0;
  font-size: 0.98rem;
  font-weight: 400;
  max-width: 38rem;
  line-height: 1.55;
}
.ff-hero-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.75rem;
}
.ff-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary) !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.ff-badge:hover {
  border-color: var(--border-strong);
  box-shadow: 0 0 16px var(--cyan-glow);
}
.ff-badge-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.ff-dot-coral { background: #60a5fa; }
.ff-dot-lilac { background: #818cf8; }
.ff-dot-sky { background: #22d3ee; }
.ff-dot-mint { background: #34d399; }

.ff-hero-chips { display: flex; flex-wrap: wrap; gap: 0.45rem; justify-content: flex-end; align-items: flex-start; }
.ff-stat-chip {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 0.4rem 0.65rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  background: var(--bg-elevated);
}

/* Memory meta */
.ff-meta-row {
  font-size: 0.78rem;
  line-height: 1.55;
  color: var(--text-muted);
  margin: 0 0 0.85rem 0;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid var(--border-subtle);
}
.ff-meta-row strong {
  color: var(--text-primary);
  font-weight: 600;
  margin-right: 0.25rem;
}
.ff-meta-sep { color: var(--text-muted); margin: 0 0.35rem; opacity: 0.7; }

/* Metrics */
[data-testid="stMetric"] {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--radius-md) !important;
  padding: 0.55rem 0.6rem !important;
  min-height: 0 !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stMetric"]:hover {
  border-color: var(--border-strong) !important;
  box-shadow: 0 0 20px var(--cyan-glow);
}
[data-testid="stMetric"] label {
  color: var(--text-muted) !important;
  font-weight: 600 !important;
  font-size: 0.72rem !important;
  letter-spacing: 0.02em;
  line-height: 1.25 !important;
  white-space: normal !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
  color: var(--text-primary) !important;
  font-weight: 700 !important;
  font-size: 0.92rem !important;
  line-height: 1.2 !important;
  white-space: normal !important;
  word-break: break-word !important;
  overflow: visible !important;
  text-overflow: clip !important;
}

/* Buttons */
.stButton > button {
  border-radius: var(--radius-sm) !important;
  font-weight: 600 !important;
  transition: box-shadow 0.2s ease, transform 0.15s ease, background 0.2s ease !important;
  border: none !important;
}
div[data-testid="stButton"] button[kind="primary"] {
  background: linear-gradient(165deg, #2dd4bf 0%, #22d3ee 55%, #06b6d4 100%) !important;
  color: #041016 !important;
  font-weight: 700 !important;
  box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.55), 0 0 24px rgba(34, 211, 238, 0.25);
}
div[data-testid="stButton"] button[kind="primary"]:hover {
  background: linear-gradient(165deg, #5eead4 0%, #67e8f9 50%, #22d3ee 100%) !important;
  box-shadow: 0 0 0 1px rgba(103, 232, 249, 0.6), 0 0 32px rgba(34, 211, 238, 0.35) !important;
}
div[data-testid="stButton"] button[kind="secondary"] {
  background: var(--bg-surface) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-subtle) !important;
}
div[data-testid="stButton"] button[kind="secondary"]:hover {
  border-color: var(--border-strong) !important;
  box-shadow: 0 0 18px var(--cyan-glow);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 0.25rem;
  background: var(--bg-surface);
  padding: 0.3rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}
.stTabs [data-baseweb="tab"] {
  border-radius: var(--radius-sm) !important;
  padding: 0.5rem 0.95rem !important;
  font-weight: 600 !important;
  color: var(--text-muted) !important;
}
.stTabs [aria-selected="true"] {
  background: rgba(34, 211, 238, 0.14) !important;
  color: var(--text-primary) !important;
  box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.35);
}

/* Inputs */
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {
  border-radius: var(--radius-sm) !important;
  background: var(--bg-deep) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-subtle) !important;
}

/* Long-form fields — monospace for notes / tasks (code-panel feel) */
.main .block-container .stTextArea textarea {
  font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, monospace !important;
  font-size: 0.86rem !important;
  line-height: 1.5 !important;
}

/* Bordered capture panel from st.container(border=True) */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.22);
}

.ff-meeting-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0 0 0.75rem 0;
  padding-bottom: 0.65rem;
  border-bottom: 1px solid var(--border-subtle);
}
.ff-meeting-head-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-secondary) !important;
}
.ff-meeting-ready {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted) !important;
}
.ff-meeting-ready-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 12px rgba(52, 211, 153, 0.55);
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.22), 0 0 20px var(--cyan-glow) !important;
}

/* Expanders */
div[data-testid="stExpander"] details {
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border-subtle) !important;
  background: var(--bg-surface) !important;
}
div[data-testid="stExpander"] summary { font-weight: 600 !important; color: var(--text-primary) !important; }

.stAlert { border-radius: var(--radius-md) !important; border: 1px solid var(--border-subtle) !important; }

h4 { color: var(--text-primary) !important; }

/* Cards */
.memory-card, .ff-memory-pin {
  position: relative;
  border-radius: var(--radius-md);
  padding: 1rem 1.15rem;
  margin-bottom: 0.85rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.2);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  animation: ff-rise 0.4s ease-out both;
}
.memory-card:hover, .ff-memory-pin:hover {
  border-color: var(--border-strong);
  box-shadow: 0 4px 28px rgba(34, 211, 238, 0.14);
}

.ff-timeline-card {
  border-left: 3px solid var(--accent);
}

.prep-section-card {
  border-radius: var(--radius-md);
  padding: 1rem 1.15rem;
  margin-bottom: 0.85rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  animation: ff-rise 0.4s ease-out both;
}
.prep-section-card:hover {
  border-color: var(--border-strong);
  box-shadow: 0 0 20px var(--cyan-glow);
}

.investor-group-title {
  font-size: 1.02rem;
  font-weight: 700;
  color: var(--text-primary) !important;
  margin: 1.2rem 0 0.55rem 0;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--border-strong);
}

.small-muted { color: var(--text-muted); font-size: 0.82rem; }

.ff-insight-board-title {
  font-size: 1.2rem;
  margin: 0.5rem 0 1rem 0;
  font-weight: 700;
  color: var(--text-primary) !important;
  letter-spacing: -0.02em;
}
.ff-insight-pin {
  border-radius: var(--radius-md);
  padding: 0.95rem 1.05rem;
  margin-bottom: 0.75rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  animation: ff-rise 0.45s ease-out both;
}
.ff-insight-pin:hover {
  border-color: var(--border-strong);
  box-shadow: 0 0 22px rgba(34, 211, 238, 0.12);
}

/* Insight card body — readable on dark background (avoid low-contrast slate hexes) */
.ff-insight-body {
  font-size: 0.95rem;
  line-height: 1.65;
  color: var(--text-secondary) !important;
}
.ff-insight-body strong {
  color: var(--text-primary) !important;
  font-weight: 600;
}
.ff-insight-body .ff-bullet {
  color: var(--accent);
  font-weight: 700;
  margin-right: 0.35rem;
}

/* Markdown body text in main column */
.main .block-container .stMarkdown p,
.main .block-container .stMarkdown li {
  color: var(--text-secondary);
}
.main .block-container .stMarkdown strong {
  color: var(--text-primary);
}

/* Dashboard: even spacing between horizontal button groups */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
  padding-left: 0.3rem !important;
  padding-right: 0.3rem !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child {
  padding-left: 0 !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
  padding-right: 0 !important;
}
.ff-stagger-0 { animation-delay: 0s; }
.ff-stagger-1 { animation-delay: 0.05s; }
.ff-stagger-2 { animation-delay: 0.1s; }
.ff-stagger-3 { animation-delay: 0.15s; }
.ff-stagger-4 { animation-delay: 0.2s; }
.ff-stagger-5 { animation-delay: 0.25s; }

.ff-footer {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.86rem;
  line-height: 1.65;
  padding: 1.5rem 0 0.5rem 0;
  margin-top: 1.5rem;
  border-top: 1px solid var(--border-subtle);
}
.ff-footer strong { color: var(--text-secondary); font-weight: 600; }

.ff-anim-rise { animation: ff-rise 0.5s ease-out both; }

.stLinkButton > a {
  border-radius: var(--radius-sm) !important;
  background: var(--bg-surface) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-subtle) !important;
}
.stLinkButton > a:hover {
  border-color: var(--accent) !important;
  box-shadow: 0 0 18px var(--cyan-glow);
}

[data-testid="stChatMessage"] { animation: ff-rise 0.35s ease-out both; }

.stCodeBlock {
  border-radius: var(--radius-sm) !important;
  border: 1px solid var(--border-subtle) !important;
  background: var(--bg-deep) !important;
}
.stCodeBlock code { color: var(--text-primary) !important; }

header[data-testid="stHeader"] {
  background: rgba(13, 17, 23, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-subtle);
}

div[data-testid="stSpinner"] > div {
  border-top-color: var(--accent) !important;
}

[data-testid="stSidebar"] {
  background: var(--bg-elevated) !important;
  border-right: 1px solid var(--border-strong) !important;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.2);
}
[data-testid="stSidebar"] .block-container {
  color: var(--text-primary);
  padding-top: 1rem !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
  gap: 0.35rem;
}
.ff-sidebar-brand {
  font-size: 1.28rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0 0 0.2rem 0;
  line-height: 1.2;
  color: var(--text-primary) !important;
}
.ff-sidebar-tag {
  font-size: 0.76rem;
  font-weight: 500;
  color: var(--text-muted) !important;
  margin: 0 0 0.65rem 0;
  line-height: 1.45;
}
[data-testid="stSidebar"] .stCaption {
  margin-top: 0.35rem !important;
  margin-bottom: 0.25rem !important;
}
"""
