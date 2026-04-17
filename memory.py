import hashlib
import json
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


DEFAULT_MEMORY_FILE = Path("memory_store.json")
# Hosted Hindsight memories API (override with HINDSIGHT_BASE_URL in .env).
DEFAULT_HINDSIGHT_BASE_URL = "https://api.hindsight.ai/v1/memories"

# Short-lived cache so Streamlit reruns do not hammer Hindsight on every frame.
_REMOTE_FETCH_CACHE: Dict[str, Tuple[float, List[Dict]]] = {}
_REMOTE_TTL_SEC = 45.0


def _hindsight_remote_cache_key(api_key: str, base_url: str) -> str:
    return hashlib.sha256(f"{api_key}|{base_url}".encode("utf-8")).hexdigest()[:32]


def invalidate_hindsight_remote_cache() -> None:
    _REMOTE_FETCH_CACHE.clear()


def _extract_memory_items_from_payload(payload: Any) -> List[Dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("data", "items", "memories", "results", "records"):
            v = payload.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def _coerce_hindsight_item_to_record(item: Dict) -> Optional[Dict]:
    """Map a Hindsight list/search row into a FounderFlow meeting dict."""
    raw_content = item.get("content")
    if isinstance(raw_content, str) and raw_content.strip():
        try:
            obj = json.loads(raw_content)
            if isinstance(obj, dict) and (
                (str(obj.get("investor_name") or "")).strip()
                or (str(obj.get("notes") or "")).strip()
            ):
                return _normalize_record(obj)
        except json.JSONDecodeError:
            pass
    if (str(item.get("investor_name") or "")).strip() or (str(item.get("notes") or "")).strip():
        return _normalize_record(dict(item))
    return None

# Realistic multi-meeting history for first-run seed + reset (cumulative over time)
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


def check_hindsight_connection(
    api_key: Optional[str],
    base_url: Optional[str] = None,
) -> bool:
    """True if Hindsight API responds successfully with this key (best-effort)."""
    if not (api_key or "").strip():
        return False
    url = (base_url or os.getenv("HINDSIGHT_BASE_URL") or "").strip() or DEFAULT_HINDSIGHT_BASE_URL
    try:
        headers = {"Authorization": f"Bearer {api_key.strip()}"}
        response = requests.get(
            url,
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
    def __init__(
        self,
        file_path: Path = DEFAULT_MEMORY_FILE,
        hindsight_api_key: Optional[str] = None,
        hindsight_base_url: Optional[str] = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.hindsight_api_key = hindsight_api_key
        self.hindsight_base_url = (
            (hindsight_base_url or "").strip() or DEFAULT_HINDSIGHT_BASE_URL
        )
        self.hindsight_enabled = bool(hindsight_api_key)
        self._ensure_local_store()

    def _ensure_local_store(self) -> None:
        if not self.file_path.exists():
            # Empty store on first run so demo rows are opt-in (dashboard: Load demo data).
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
        """Replace local store (no per-row Hindsight posts — use for demo reset)."""
        invalidate_hindsight_remote_cache()
        self._write_all([dict(r) for r in records])

    def clear_all(self) -> None:
        """Remove all local memories."""
        invalidate_hindsight_remote_cache()
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
            invalidate_hindsight_remote_cache()
            self._write_all(rows)
        return added

    def _list_hindsight_remote_uncached(self) -> List[Dict]:
        """Fetch memories from Hindsight (list / high limit). Returns FounderFlow-shaped rows."""
        if not self.hindsight_enabled:
            return []
        try:
            headers = {"Authorization": f"Bearer {self.hindsight_api_key}"}
            response = requests.get(
                self.hindsight_base_url,
                headers=headers,
                params={"limit": 500},
                timeout=20,
            )
            if response.status_code not in (200, 201):
                return []
            payload = response.json()
            raw_items = _extract_memory_items_from_payload(payload)
            out: List[Dict] = []
            for item in raw_items:
                rec = _coerce_hindsight_item_to_record(item)
                if rec:
                    out.append(rec)
            return out
        except Exception:
            return []

    def _list_hindsight_remote_cached(self) -> List[Dict]:
        if not self.hindsight_enabled:
            return []
        ck = _hindsight_remote_cache_key(
            self.hindsight_api_key or "",
            self.hindsight_base_url,
        )
        now = time.monotonic()
        hit = _REMOTE_FETCH_CACHE.get(ck)
        if hit and (now - hit[0] < _REMOTE_TTL_SEC):
            return hit[1]
        rows = self._list_hindsight_remote_uncached()
        _REMOTE_FETCH_CACHE[ck] = (now, rows)
        return rows

    def merge_hindsight_into_local(self) -> Tuple[int, str]:
        """Pull every row from Hindsight and append rows missing from local JSON."""
        invalidate_hindsight_remote_cache()
        if not self.hindsight_enabled:
            return 0, "Add HINDSIGHT_API_KEY to .env and restart the app."
        remote = self._list_hindsight_remote_uncached()
        if not remote:
            return 0, "No meetings parsed from Hindsight (empty project, wrong URL, or API shape mismatch)."
        existing = {_memory_dedupe_key(r) for r in self._read_all()}
        rows = self._read_all()
        added = 0
        for r in remote:
            norm = _normalize_record(dict(r))
            key = _memory_dedupe_key(norm)
            if key in existing:
                continue
            rows.append(norm)
            existing.add(key)
            added += 1
        if added:
            self._write_all(rows)
            return added, "ok"
        return 0, "Every Hindsight row is already in your local memory_store.json."

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
                self.hindsight_base_url,
                headers=headers,
                json=payload,
                timeout=10,
            )
            ok = response.status_code in {200, 201, 202}
            if ok:
                invalidate_hindsight_remote_cache()
            return ok
        except Exception:
            return False

    def _search_hindsight(self, investor_name: str) -> List[Dict]:
        if not self.hindsight_enabled:
            return []
        try:
            headers = {"Authorization": f"Bearer {self.hindsight_api_key}"}
            response = requests.get(
                self.hindsight_base_url,
                headers=headers,
                params={"query": investor_name},
                timeout=10,
            )
            if response.status_code != 200:
                return []
            data = response.json()
            raw_items = _extract_memory_items_from_payload(data)
            parsed: List[Dict] = []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                rec = _coerce_hindsight_item_to_record(item)
                if not rec:
                    continue
                inv = rec.get("investor_name", "")
                if _investor_matches_query(inv, investor_name):
                    parsed.append(rec)
            return parsed
        except Exception:
            return []

    def save_memory(self, record: Dict) -> Dict[str, Any]:
        """Append one meeting. Skips write if an identical logical row already exists (prevents duplicate saves)."""
        normalized = _normalize_record(record)
        local_records = self._read_all()
        new_key = _memory_dedupe_key(normalized)
        if any(_memory_dedupe_key(r) == new_key for r in local_records):
            return {"local_saved": False, "hindsight_saved": False, "duplicate": True}
        local_records.append(normalized)
        self._write_all(local_records)
        hindsight_ok = self._save_to_hindsight(normalized)
        return {"local_saved": True, "hindsight_saved": hindsight_ok, "duplicate": False}

    def list_all(self) -> List[Dict]:
        """Local JSON plus Hindsight cloud rows (deduped) when an API key is set."""
        local = self._read_all()
        if not self.hindsight_enabled:
            return local
        remote = self._list_hindsight_remote_cached()
        if not remote:
            return local
        return dedupe_memories(local + remote)

    def delete_memory(self, record: Dict) -> bool:
        """Remove one local row matching the same logical fields as record."""
        target = _memory_dedupe_key(_normalize_record(record))
        rows = self._read_all()
        for i, row in enumerate(rows):
            if _memory_dedupe_key(row) == target:
                rows.pop(i)
                invalidate_hindsight_remote_cache()
                self._write_all(rows)
                return True
        return False

    def get_memories_for_investor(self, investor_name: str) -> List[Dict]:
        q = (investor_name or "").strip()
        pool = self.list_all() if self.hindsight_enabled else self._read_all()
        local_matches = [
            item
            for item in pool
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
    api_key = os.getenv("HINDSIGHT_API_KEY", "").strip() or None
    base = os.getenv("HINDSIGHT_BASE_URL", "").strip() or None
    return MemoryStore(
        hindsight_api_key=api_key,
        hindsight_base_url=base,
    )
