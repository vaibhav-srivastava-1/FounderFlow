import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests


DEFAULT_MEMORY_FILE = Path("memory_store.json")
HINDSIGHT_BASE_URL = "https://api.hindsight.ai/v1/memories"

# Realistic multi-meeting history for first-run seed + reset (cumulative over time)
DEMO_DATA: List[Dict] = [
    {
        "investor_name": "Rahul Mehta",
        "notes": "Initial intro call. Asked CAC and burn rate.",
        "objections": "Focused on efficiency of spend vs. growth.",
        "promises": "Send pitch deck.",
        "date": "2026-04-10",
    },
    {
        "investor_name": "Rahul Mehta",
        "notes": "Follow-up meeting. Liked traction growth.",
        "objections": "Concerned about retention.",
        "promises": "Share retention dashboard.",
        "date": "2026-04-15",
    },
    {
        "investor_name": "Rahul Mehta",
        "notes": "Requested next round ownership details.",
        "objections": "",
        "promises": "",
        "date": "2026-04-18",
    },
    {
        "investor_name": "Priya Sharma",
        "notes": "Asked GTM strategy.",
        "objections": "",
        "promises": "",
        "date": "2026-04-12",
    },
    {
        "investor_name": "Priya Sharma",
        "notes": "Interested in partnerships.",
        "objections": "Needs revenue predictability.",
        "promises": "",
        "date": "2026-04-17",
    },
    {
        "investor_name": "Priya Sharma",
        "notes": "Asked about expansion roadmap.",
        "objections": "",
        "promises": "",
        "date": "2026-04-18",
    },
    {
        "investor_name": "Arjun Kapoor",
        "notes": "Angel investor. Loved founder energy.",
        "objections": "Needs unit economics clarity.",
        "promises": "",
        "date": "2026-04-11",
    },
]


def normalize_investor_name(name: str) -> str:
    """Title-case each word: rahul mehta / RAHUL MEHTA → Rahul Mehta."""
    parts = name.strip().split()
    if not parts:
        return ""
    return " ".join(p[:1].upper() + p[1:].lower() if p else p for p in parts)


def _investor_matches_query(stored_name: str, query: str) -> bool:
    s = (stored_name or "").strip().lower()
    q = (query or "").strip().lower()
    if not q or not s:
        return False
    return q in s or s in q


def _memory_dedupe_key(m: Dict) -> Tuple:
    return (
        (m.get("investor_name") or "").strip().lower(),
        m.get("date") or "",
        (m.get("notes") or "").strip(),
        (m.get("objections") or "").strip(),
        (m.get("promises") or "").strip(),
    )


def dedupe_memories(items: List[Dict]) -> List[Dict]:
    seen = set()
    out: List[Dict] = []
    for m in sorted(items, key=lambda x: x.get("date", "")):
        key = _memory_dedupe_key(m)
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def memory_fingerprint(record: Dict) -> str:
    """Stable id for UI keys and delete matching (after normalization)."""
    raw = "|".join(str(x) for x in _memory_dedupe_key(record))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def count_pending_promises(memories: List[Dict]) -> int:
    """Count meetings with a non-empty promises field (MVP proxy for open follow-ups)."""
    return sum(1 for m in memories if (m.get("promises") or "").strip())


def check_hindsight_connection(api_key: Optional[str]) -> bool:
    """True if Hindsight API responds successfully with this key (best-effort)."""
    if not (api_key or "").strip():
        return False
    try:
        headers = {"Authorization": f"Bearer {api_key.strip()}"}
        response = requests.get(
            HINDSIGHT_BASE_URL,
            headers=headers,
            params={"limit": 1},
            timeout=6,
        )
        return response.status_code in (200, 201)
    except Exception:
        return False


def _normalize_record(record: Dict) -> Dict:
    normalized = dict(record)
    if normalized.get("investor_name"):
        normalized["investor_name"] = normalize_investor_name(
            str(normalized["investor_name"])
        )
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
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
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

    def replace_all(self, records: List[Dict]) -> None:
        """Replace local store (no per-row Hindsight posts — use for demo reset)."""
        self._write_all([dict(r) for r in records])

    def clear_all(self) -> None:
        """Remove all local memories."""
        self._write_all([])

    def append_demo_records(self, records: List[Dict]) -> int:
        """Append demo rows that are not already present. Returns number added."""
        existing = {_memory_dedupe_key(x) for x in self._read_all()}
        added = 0
        rows = self._read_all()
        for raw in records:
            norm = _normalize_record(dict(raw))
            key = _memory_dedupe_key(norm)
            if key in existing:
                continue
            rows.append(norm)
            existing.add(key)
            added += 1
        if added:
            self._write_all(rows)
        return added

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
                        rec = _normalize_record(parsed_item)
                        inv = rec.get("investor_name", "")
                        if _investor_matches_query(inv, investor_name):
                            parsed.append(rec)
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

    def delete_memory(self, record: Dict) -> bool:
        """Remove one local row matching the same logical fields as record."""
        target = _memory_dedupe_key(_normalize_record(record))
        rows = self._read_all()
        for i, row in enumerate(rows):
            if _memory_dedupe_key(row) == target:
                rows.pop(i)
                self._write_all(rows)
                return True
        return False

    def get_memories_for_investor(self, investor_name: str) -> List[Dict]:
        q = (investor_name or "").strip()
        local_matches = [
            item
            for item in self._read_all()
            if _investor_matches_query(item.get("investor_name", ""), q)
        ]
        if self.hindsight_enabled:
            remote_matches = self._search_hindsight(q)
            combined = local_matches + remote_matches
            return dedupe_memories(combined)
        return dedupe_memories(local_matches)


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
