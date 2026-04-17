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


def build_prepare_meeting_prompt(investor_name: str, memories_text: str) -> str:
    return f"""
Investor Name: {investor_name}

Meeting Memory Context:
{memories_text}

Create a preparation brief for the founder.
Use this exact structure:

Last meeting summary:
Investor objections:
Pending promises:
Suggested talking points:
Risks:
Next actions:
""".strip()


def build_email_prompt(investor_name: str, memories_text: str) -> str:
    return f"""
Write a professional investor follow-up email using past meeting context.

Investor Name: {investor_name}

Meeting Memory Context:
{memories_text}

Keep it concise and warm. Include:
- appreciation
- recap of key discussion points
- promised follow-ups
- clear next step or call to action
""".strip()
