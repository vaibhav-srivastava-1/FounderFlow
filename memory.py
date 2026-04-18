import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv


DEFAULT_MEMORY_FILE = Path("memory_store.json")

# Realistic multi-meeting history for first-run seed + judge demo
DEMO_DATA: List[Dict] = [
    {
        "investor_name": "Rahul Mehta",
        "notes": "Initial intro call. Asked CAC and burn rate.",
        "objections": "Focused on efficiency of spend vs. growth.",
        "promises": "Send pitch deck.",
        "date": "2026-04-10",
        "created_at": "2026-04-10T17:05:00",
    },
    {
        "investor_name": "Rahul Mehta",
        "notes": "Follow-up meeting. Liked traction growth.",
        "objections": "Concerned about retention.",
        "promises": "Share retention dashboard.",
        "date": "2026-04-15",
        "created_at": "2026-04-15T11:40:00",
    },
    {
        "investor_name": "Rahul Mehta",
        "notes": "Requested next round ownership details.",
        "objections": "",
        "promises": "",
        "date": "2026-04-18",
        "created_at": "2026-04-18T09:15:00",
    },
    {
        "investor_name": "Priya Sharma",
        "notes": "Asked GTM strategy.",
        "objections": "",
        "promises": "",
        "date": "2026-04-12",
        "created_at": "2026-04-12T16:20:00",
    },
    {
        "investor_name": "Priya Sharma",
        "notes": "Interested in partnerships.",
        "objections": "Needs revenue predictability.",
        "promises": "",
        "date": "2026-04-17",
        "created_at": "2026-04-17T14:55:00",
    },
    {
        "investor_name": "Priya Sharma",
        "notes": "Asked about expansion roadmap.",
        "objections": "",
        "promises": "",
        "date": "2026-04-18",
        "created_at": "2026-04-18T10:08:00",
    },
    {
        "investor_name": "Arjun Kapoor",
        "notes": "Angel investor. Loved founder energy.",
        "objections": "Needs unit economics clarity.",
        "promises": "",
        "date": "2026-04-11",
        "created_at": "2026-04-11T13:30:00",
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


def _normalize_record(record: Dict) -> Dict:
    normalized = dict(record)
    if normalized.get("investor_name"):
        normalized["investor_name"] = normalize_investor_name(
            str(normalized["investor_name"])
        )
    if not normalized.get("date") or normalized.get("date") == "today":
        normalized["date"] = datetime.now().strftime("%Y-%m-%d")
    if not normalized.get("created_at"):
        d = normalized.get("date") or ""
        try:
            normalized["created_at"] = (
                datetime.strptime(d, "%Y-%m-%d")
                .replace(hour=12, minute=0, second=0)
                .isoformat(timespec="seconds")
            )
        except ValueError:
            normalized["created_at"] = datetime.now().isoformat(timespec="seconds")
    return normalized


class MemoryStore:
    """Investor meeting memories persisted only in local JSON (memory_store.json)."""

    def __init__(self, file_path: Path = DEFAULT_MEMORY_FILE) -> None:
        self.file_path = Path(file_path)
        self._ensure_local_store()

    def _ensure_local_store(self) -> None:
        if not self.file_path.exists():
            self._write_all([])
            return

        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                self._write_all([])
        except Exception:
            self._write_all([])

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
        """Replace local store entirely."""
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

    def save_memory(self, record: Dict) -> Dict[str, Any]:
        """Append one meeting. Skips write if an identical logical row already exists."""
        normalized = _normalize_record(record)
        local_records = self._read_all()
        new_key = _memory_dedupe_key(normalized)
        if any(_memory_dedupe_key(r) == new_key for r in local_records):
            return {"local_saved": False, "hindsight_saved": False, "duplicate": True}
        local_records.append(normalized)
        self._write_all(local_records)
        return {"local_saved": True, "hindsight_saved": False, "duplicate": False}

    def list_all(self) -> List[Dict]:
        """All rows from local JSON only."""
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
        pool = self.list_all()
        matches = [
            item
            for item in pool
            if _investor_matches_query(item.get("investor_name", ""), q)
        ]
        return dedupe_memories(matches)


def memories_to_text(memories: List[Dict]) -> str:
    if not memories:
        return "No prior meetings found."
    lines = []
    for idx, m in enumerate(memories, start=1):
        inv = (m.get("investor_name") or "").strip() or "Unknown investor"
        lines.append(
            (
                f"Meeting {idx} — Investor: {inv} — Date: {m.get('date', 'unknown date')}\n"
                f"- Notes: {m.get('notes', '')}\n"
                f"- Objections: {m.get('objections', '')}\n"
                f"- Promises: {m.get('promises', '')}"
            )
        )
    return "\n\n".join(lines)


def memory_chat_context_text(rows: List[Dict]) -> str:
    """Rich text for memory chat: global timeline + per-investor blocks (#1 = newest)."""
    if not rows:
        return "No prior meetings found."

    chrono = sorted(
        rows,
        key=lambda x: (x.get("date") or "", x.get("investor_name") or ""),
    )
    parts: List[str] = [
        "=== Section A: All meetings (chronological, oldest → newest) ===\n",
        memories_to_text(chrono),
        "\n=== Section B: By investor (within each investor, #1 = most recent meeting, then older) ===\n",
    ]

    by_name: Dict[str, List[Dict]] = defaultdict(list)
    for m in rows:
        inv = (m.get("investor_name") or "").strip() or "Unknown investor"
        by_name[inv].append(dict(m))

    for inv in sorted(by_name.keys(), key=lambda s: s.lower()):
        items = sorted(
            by_name[inv],
            key=lambda x: x.get("date") or "",
            reverse=True,
        )
        n = len(items)
        parts.append(f"\n--- {inv} — {n} meeting(s) ---")
        rank_words = {
            1: "most recent",
            2: "second most recent",
            3: "third most recent",
            4: "fourth most recent",
            5: "fifth most recent",
        }
        for i, m in enumerate(items, start=1):
            label = rank_words.get(i, f"#{i} from present (older)")
            parts.append(
                f"\n  #{i} ({label}) — Date: {m.get('date', 'unknown')}\n"
                f"  - Notes: {m.get('notes', '')}\n"
                f"  - Objections: {m.get('objections', '')}\n"
                f"  - Promises: {m.get('promises', '')}"
            )

    return "\n".join(parts)


def create_store_from_env() -> MemoryStore:
    load_dotenv()
    return MemoryStore()
