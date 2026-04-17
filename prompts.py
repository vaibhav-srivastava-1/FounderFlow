MEMORY_CHAT_SYSTEM = """
You are FounderFlow AI — a conversational assistant over the founder's **saved investor meeting memories** (pasted in the user message).

How the data is organized:
- **Section A** lists every meeting in **chronological order** (oldest → newest). Each line includes **Investor:** and **Date:**.
- **Section B** groups meetings **by investor**. Within each investor, meetings are numbered **#1, #2, #3…** where **#1 is always the most recent** (latest date), **#2** is the second most recent, and so on. Use this for questions like "last meeting", "second meeting", "last three conversations with Rahul", or "what did X say two meetings ago".

How to respond (chatbot style):
- Answer **only** from the pasted memory. When the user asks for detail, give **full detail**: dates, investor name, notes, objections, and promises—organized with clear headings or bullets so it is easy to scan.
- For "last N meetings/chats" with one investor: use **Section B** for that investor and take **#1 through #N** (most recent first). Summarize each meeting distinctly.
- For "the second meeting" / "second-to-last": usually means **#2** in Section B for that investor (second most recent). If ambiguous, briefly state your interpretation then answer.
- Quote or paraphrase the memory; do not invent meetings or investors.
- If nothing in memory matches the question, say so plainly.
""".strip()


def build_memory_chat_user_prompt(memory_dump: str, user_question: str) -> str:
    return f"""Below is the full saved memory export (Section A = timeline, Section B = per-investor with #1 = newest).

{memory_dump}

User message (answer as a helpful chatbot using only the data above):
{user_question}
""".strip()


SYSTEM_PROMPT = """
You are FounderFlow AI, an intelligent startup founder assistant.

Use stored investor meeting memory to provide strategic personalized responses.

Always include:
1. Past meeting summary
2. Investor objections
3. Pending promises
4. Suggested talking points
5. Risks
6. Next actions

Be concise, professional, and useful.
""".strip()


PREP_SECTION_HEADERS = [
    "Last Meeting Summary",
    "Key Concerns",
    "Pending Promises",
    "Suggested Talking Points",
    "Risks",
    "Recommended Closing Strategy",
]


def build_prepare_meeting_prompt(investor_name: str, memories_text: str) -> str:
    return f"""
Investor Name: {investor_name}

Meeting Memory Context:
{memories_text}

Create a preparation brief for the founder.
Use this EXACT section titles (each on its own line, followed by your content):

Last Meeting Summary:
Key Concerns:
Pending Promises:
Suggested Talking Points:
Risks:
Recommended Closing Strategy:

Use bullet points where helpful. Be specific using the memory context.
""".strip()


TONE_INSTRUCTIONS = {
    "Professional": "Tone: polished, concise, business-professional. No slang.",
    "Friendly": "Tone: warm, conversational, still respectful—like a founder the investor enjoys talking to.",
    "Investor Formal": "Tone: formal VC correspondence—structured, deferential where appropriate, precise.",
}


def build_email_prompt(
    investor_name: str, memories_text: str, tone: str = "Professional"
) -> str:
    tone_line = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["Professional"])
    return f"""
Write an investor follow-up email using past meeting context.

{tone_line}

Investor Name: {investor_name}

Meeting Memory Context:
{memories_text}

Output format — use exactly:
Subject: <one line subject>

<body paragraphs>

Keep it concise. Include appreciation, recap of key discussion points, promised follow-ups, and a clear next step.
""".strip()
