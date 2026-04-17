import os
from typing import Optional

import requests

from prompts import SYSTEM_PROMPT


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqClient:
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "").strip()
        self.model = model

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def complete(self, user_prompt: str, temperature: float = 0.3) -> str:
        if not self.configured:
            return (
                "Groq API key is missing. Add GROQ_API_KEY in your .env file to get AI-generated output."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return "No response received from Groq."
            return choices[0]["message"]["content"].strip()
        except requests.RequestException as exc:
            return f"Groq request failed: {exc}"
