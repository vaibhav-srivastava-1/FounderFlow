import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests


DEFAULT_MEMORY_FILE = Path("memory_store.json")
HINDSIGHT_BASE_URL = "https://api.hindsight.ai/v1/memories"


DEMO_DATA = [
    {
        "investor_name": "Rahul Mehta",
        "notes": "Asked CAC and growth metrics.",
        "objections": "High CAC concerns.",
        "promises": "Send updated pitch deck.",
        "date": "today",
    },
    {
        "investor_name": "Priya Sharma",
        "notes": "Asked traction metrics and monthly active users.",
        "objections": "Needs GTM clarity.",
        "promises": "Share GTM breakdown and customer pipeline.",
        "date": "today",
    },
]


def _normalize_record(record: Dict) -> Dict:
    normalized = dict(record)
    if not normalized.get("date") or normalized.get("date") == "today":
        normalized["date"] = datetime.now().strftime("%Y-%m-%d")
    return normalized


class MemoryStore:
    def __init__(
        self,
        file_path: Path = DEFAULT_MEMORY_FILE,
        hindsight_api_key: Optional[str] = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.hindsight_api_key = hindsight_api_key
        self.hindsight_enabled = bool(hindsight_api_key)
        self._ensure_local_store()

    def _ensure_local_store(self) -> None:
        if not self.file_path.exists():
            self._write_all(DEMO_DATA)
            return

        try:
            records = self._read_all()
            if not records:
                self._write_all(DEMO_DATA)
        except Exception:
            self._write_all(DEMO_DATA)

    def _read_all(self) -> List[Dict]:
        with self.file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return [_normalize_record(item) for item in data if isinstance(item, dict)]

    def _write_all(self, records: List[Dict]) -> None:
        normalized = [_normalize_record(item) for item in records]
        with self.file_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2)

    def _save_to_hindsight(self, record: Dict) -> bool:
        if not self.hindsight_enabled:
            return False
        try:
            payload = {
                "content": json.dumps(record),
                "metadata": {"investor_name": record.get("investor_name", "")},
            }
            headers = {"Authorization": f"Bearer {self.hindsight_api_key}"}
            response = requests.post(
                HINDSIGHT_BASE_URL,
                headers=headers,
                json=payload,
                timeout=10,
            )
            return response.status_code in {200, 201, 202}
        except Exception:
            return False

    def _search_hindsight(self, investor_name: str) -> List[Dict]:
        if not self.hindsight_enabled:
            return []
        try:
            headers = {"Authorization": f"Bearer {self.hindsight_api_key}"}
            response = requests.get(
                HINDSIGHT_BASE_URL,
                headers=headers,
                params={"query": investor_name},
                timeout=10,
            )
            if response.status_code != 200:
                return []
            data = response.json()
            raw_items = data.get("data", []) if isinstance(data, dict) else []
            parsed: List[Dict] = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not content:
                    continue
                try:
                    parsed_item = json.loads(content)
                    if isinstance(parsed_item, dict):
                        parsed.append(_normalize_record(parsed_item))
                except Exception:
                    continue
            return parsed
        except Exception:
            return []

    def save_memory(self, record: Dict) -> Dict[str, bool]:
        normalized = _normalize_record(record)
        local_records = self._read_all()
        local_records.append(normalized)
        self._write_all(local_records)
        hindsight_ok = self._save_to_hindsight(normalized)
        return {"local_saved": True, "hindsight_saved": hindsight_ok}

    def list_all(self) -> List[Dict]:
        return self._read_all()

    def get_memories_for_investor(self, investor_name: str) -> List[Dict]:
        name_lower = investor_name.strip().lower()
        local_matches = [
            item
            for item in self._read_all()
            if item.get("investor_name", "").strip().lower() == name_lower
        ]
        if self.hindsight_enabled:
            remote_matches = self._search_hindsight(investor_name)
            combined = local_matches + remote_matches
            return sorted(combined, key=lambda x: x.get("date", ""))
        return sorted(local_matches, key=lambda x: x.get("date", ""))


def memories_to_text(memories: List[Dict]) -> str:
    if not memories:
        return "No prior meetings found."
    lines = []
    for idx, m in enumerate(memories, start=1):
        lines.append(
            (
                f"Meeting {idx} ({m.get('date', 'unknown date')}):\n"
                f"- Notes: {m.get('notes', '')}\n"
                f"- Objections: {m.get('objections', '')}\n"
                f"- Promises: {m.get('promises', '')}"
            )
        )
    return "\n\n".join(lines)


def create_store_from_env() -> MemoryStore:
    api_key = os.getenv("HINDSIGHT_API_KEY", "").strip() or None
    return MemoryStore(hindsight_api_key=api_key)
