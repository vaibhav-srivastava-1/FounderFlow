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
