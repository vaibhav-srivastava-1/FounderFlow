import html
import re
import urllib.parse
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

from llm import GroqClient
from memory import (
    DEMO_DATA,
    count_pending_promises,
    create_store_from_env,
    memories_to_text,
    memory_chat_context_text,
    memory_fingerprint,
    normalize_investor_name,
)
from prompts import (
    MEMORY_CHAT_SYSTEM,
    PREP_SECTION_HEADERS,
    build_email_prompt,
    build_memory_chat_user_prompt,
    build_prepare_meeting_prompt,
)
from theme_css import DARK_PRO_THEME_CSS as FF_GLOBAL_CSS, FF_GOOGLE_FONTS

load_dotenv()

# --- Optional: Streamlit Community Cloud / Docker deploy ---
# Uncomment to map st.secrets into os.environ (e.g. GROQ_API_KEY) when deployed online.
# def _streamlit_cloud_secrets_to_env() -> None:
#     try:
#         sec = getattr(st, "secrets", None)
#         if sec is None:
#             return
#         for k in ("GROQ_API_KEY",):
#             try:
#                 if k not in sec:
#                     continue
#                 if (os.environ.get(k) or "").strip():
#                     continue
#                 val = str(sec[k]).strip()
#                 if val:
#                     os.environ[k] = val
#             except Exception:
#                 continue
#     except Exception:
#         pass


st.set_page_config(
    page_title="FounderFlow AI",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# _streamlit_cloud_secrets_to_env()

memory_store = create_store_from_env()
llm_client = GroqClient()

st.markdown(
    f'<link rel="stylesheet" href="{FF_GOOGLE_FONTS}">',
    unsafe_allow_html=True,
)
st.markdown(f"<style>{FF_GLOBAL_CSS}</style>", unsafe_allow_html=True)

st.markdown(
    '<div class="ff-pro-band">'
    "<span>Investor relations workspace</span>"
    "<span>Structured memory · Brief generation</span>"
    "</div>",
    unsafe_allow_html=True,
)

if "prepare_investor" not in st.session_state:
    st.session_state.prepare_investor = ""
if "email_investor" not in st.session_state:
    st.session_state.email_investor = ""
if "email_tone" not in st.session_state:
    st.session_state.email_tone = "Professional"
if "email_draft" not in st.session_state:
    st.session_state.email_draft = ""
if "judge_banner" not in st.session_state:
    st.session_state.judge_banner = ""
if "add_form_investor" not in st.session_state:
    st.session_state.add_form_investor = ""
if "add_form_notes" not in st.session_state:
    st.session_state.add_form_notes = ""
if "add_form_objections" not in st.session_state:
    st.session_state.add_form_objections = ""
if "add_form_promises" not in st.session_state:
    st.session_state.add_form_promises = ""
if "demo_fill_idx" not in st.session_state:
    st.session_state.demo_fill_idx = 0
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "_memory_chat_pending" not in st.session_state:
    st.session_state._memory_chat_pending = False
if "save_meeting_flash" not in st.session_state:
    st.session_state.save_meeting_flash = None
if "clear_add_form_after_save" not in st.session_state:
    st.session_state.clear_add_form_after_save = False
if "show_memory_compare" not in st.session_state:
    st.session_state.show_memory_compare = False
if "ff_nav_page" not in st.session_state:
    st.session_state.ff_nav_page = "overview"
if "ff_dashboard_flash" not in st.session_state:
    st.session_state.ff_dashboard_flash = None


def _parse_record_instant(created_at: Optional[str], meeting_date: Optional[str]) -> datetime:
    if created_at:
        raw = str(created_at).strip()
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    d = (meeting_date or "").strip()
    try:
        return datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        return datetime.now()


def format_relative_logged_ago(created_at: Optional[str], meeting_date: Optional[str]) -> str:
    """Human-readable time since this memory row was logged (professional copy)."""
    t = _parse_record_instant(created_at, meeting_date)
    delta = datetime.now() - t
    sec = max(0, int(delta.total_seconds()))
    if sec < 45:
        return "just now"
    if sec < 90:
        return "1 minute ago"
    mins = sec // 60
    if mins < 60:
        return "1 minute ago" if mins == 1 else f"{mins} minutes ago"
    hrs = mins // 60
    if hrs < 24:
        return "1 hour ago" if hrs == 1 else f"{hrs} hours ago"
    days = hrs // 24
    if days < 14:
        return "1 day ago" if days == 1 else f"{days} days ago"
    weeks = days // 7
    if weeks < 8:
        return "1 week ago" if weeks == 1 else f"{weeks} weeks ago"
    mons = days // 30
    if mons < 12:
        return "1 month ago" if mons == 1 else f"{mons} months ago"
    yrs = days // 365
    return "1 year ago" if yrs == 1 else f"{yrs} years ago"


def _memory_meta_row_html(item: Dict) -> str:
    meeting = html.escape(str(item.get("date") or "—"))
    ago = html.escape(format_relative_logged_ago(item.get("created_at"), item.get("date")))
    return (
        '<div class="ff-meta-row">'
        f"<strong>Meeting date</strong> {meeting}"
        f"<span class='ff-meta-sep'>|</span>"
        f"<strong>Logged</strong> {ago}"
        "</div>"
    )


def _apply_demo_row_to_add_form(row: Dict) -> None:
    """Pre-fill Add Meeting fields from a demo record (user can edit, then Save)."""
    st.session_state.add_form_investor = str(row.get("investor_name", ""))
    st.session_state.add_form_notes = str(row.get("notes", ""))
    st.session_state.add_form_objections = str(row.get("objections", "") or "")
    st.session_state.add_form_promises = str(row.get("promises", "") or "")


def _memory_dump_for_chat() -> str:
    """Structured dump for chatbot-style Q&A (timeline + per-investor newest-first)."""
    return memory_chat_context_text(memory_store.list_all())


def parse_email_subject_body(email_text: str) -> Tuple[str, str]:
    t = email_text.strip()
    subj = "Follow-up"
    body = t
    m = re.match(r"(?is)^\s*Subject\s*:\s*(.+?)(?:\r?\n|$)", t)
    if m:
        subj = m.group(1).strip()
        body = t[m.end() :].strip()
    return subj, body


def gmail_compose_url(subject: str, body: str) -> str:
    return (
        "https://mail.google.com/mail/?view=cm&fs=1&"
        f"su={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
    )


def mailto_url(subject: str, body: str) -> str:
    return "mailto:?" + urllib.parse.urlencode({"subject": subject, "body": body})


def parse_prep_sections(text: str) -> Dict[str, str]:
    """Extract labeled prep sections from model output."""
    result: Dict[str, str] = {}
    positions: List[Tuple[int, str]] = []
    for h in PREP_SECTION_HEADERS:
        m = re.search(rf"(?mi)^{re.escape(h)}\s*:", text)
        if m:
            positions.append((m.start(), h))
    positions.sort(key=lambda x: x[0])
    for j, (start, h) in enumerate(positions):
        end = positions[j + 1][0] if j + 1 < len(positions) else len(text)
        chunk = text[start:end]
        lines = chunk.split("\n", 1)
        body = lines[1].strip() if len(lines) > 1 else ""
        result[h] = body
    return result


def _html_multiline(value: object) -> str:
    return html.escape(str(value or "")).replace("\n", "<br/>")


def _insight_line_to_html(line: str) -> str:
    """Convert a single-line insight with **bold** spans to safe HTML."""
    out: List[str] = []
    rest = line
    while rest:
        m = re.search(r"\*\*(.+?)\*\*", rest)
        if not m:
            out.append(html.escape(rest))
            break
        if m.start() > 0:
            out.append(html.escape(rest[: m.start()]))
        out.append("<strong>" + html.escape(m.group(1)) + "</strong>")
        rest = rest[m.end() :]
    return "".join(out)


def _render_prep_cards(text: str, fallback_text: str) -> None:
    parsed = parse_prep_sections(text)
    if len(parsed) < 3:
        parsed = parse_prep_sections(fallback_text)
    if len(parsed) >= 3:
        for h in PREP_SECTION_HEADERS:
            if h not in parsed:
                continue
            body_esc = html.escape(parsed[h]).replace("\n", "<br/>")
            st.markdown(
                f'<div class="prep-section-card">'
                f"<p style='margin:0 0 10px 0;font-weight:700'>{html.escape(h)}</p>"
                f"<div style='font-size:0.95rem;line-height:1.55'>{body_esc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.text(text or fallback_text)


def _render_timeline_newest_first(memories: List[Dict]) -> None:
    ordered = sorted(
        memories,
        key=lambda x: x.get("date", ""),
        reverse=True,
    )
    for i, m in enumerate(ordered):
        notes = m.get("notes", "") or "—"
        obj = m.get("objections", "") or "—"
        prom = m.get("promises", "") or "—"
        st.markdown(
            f'<div class="memory-card ff-memory-pin ff-timeline-card ff-stagger-{i % 6}">'
            f"{_memory_meta_row_html(m)}"
            f"<b>Notes:</b> {_html_multiline(notes)}<br>"
            f"<b>Concerns:</b> {_html_multiline(obj)}<br>"
            f"<b>Promises:</b> {_html_multiline(prom)}"
            f"</div>",
            unsafe_allow_html=True,
        )


def _founder_insights(rows: List[Dict]) -> List[str]:
    insights: List[str] = []
    if not rows:
        return ["Save a few meetings to unlock AI-style pattern insights."]

    by_name: Dict[str, List[Dict]] = defaultdict(list)
    for r in rows:
        by_name[r.get("investor_name") or "Unknown"].append(r)

    rahul = by_name.get("Rahul Mehta", [])
    eff_hits = 0
    for m in rahul:
        blob = f"{m.get('notes', '')} {m.get('objections', '')}".lower()
        for kw in ("cac", "burn", "burn rate", "efficiency", "unit economics"):
            if kw in blob:
                eff_hits += 1
                break
    if len(rahul) >= 2 and eff_hits >= 1:
        insights.append(
            "**Rahul Mehta** repeatedly presses **efficiency metrics** (CAC, burn)—lead with crisp numbers."
        )
    elif rahul and eff_hits:
        insights.append(
            "**Rahul Mehta** is focused on **efficiency and unit economics** in your narrative."
        )

    priya = by_name.get("Priya Sharma", [])
    priya_blob = " ".join(
        f"{m.get('notes', '')} {m.get('objections', '')}" for m in priya
    ).lower()
    if "revenue" in priya_blob or "predictability" in priya_blob:
        insights.append(
            "**Priya Sharma** cares about **revenue predictability** and **GTM depth**—tie partnerships to pipeline."
        )

    pending = count_pending_promises(rows)
    if pending >= 3:
        insights.append(
            f"**{pending} logged follow-ups** still have promises attached—close the loop before the next call."
        )
    elif pending:
        insights.append(
            f"**{pending} meeting(s)** include open promises—review before you pitch again."
        )

    ret_n = sum(
        1
        for m in rows
        if "retention" in f"{m.get('notes', '')} {m.get('objections', '')}".lower()
    )
    if ret_n >= 2:
        insights.append(
            "**Retention** shows up multiple times—prepare cohort charts and a clear story."
        )
    elif ret_n == 1:
        insights.append(
            "**Retention** has surfaced—have one sharp proof point ready."
        )

    if not insights:
        insights.append(
            "Patterns will appear as you add objections, promises, and richer notes."
        )
    return insights


def _render_memory_cards_grouped(memories: List[Dict]) -> None:
    if not memories:
        st.info("No meeting memories found yet.")
        return

    by_name: Dict[str, List[Dict]] = {}
    for item in memories:
        name = item.get("investor_name") or "Unknown Investor"
        by_name.setdefault(name, []).append(item)

    def latest_date(items: List[Dict]) -> str:
        return max((x.get("date") or "" for x in items), default="")

    sorted_names = sorted(
        by_name.keys(),
        key=lambda n: latest_date(by_name[n]),
        reverse=True,
    )

    for name in sorted_names:
        items = sorted(
            by_name[name],
            key=lambda x: x.get("date", ""),
            reverse=True,
        )
        n_meet = len(items)
        label = f"{n_meet} meeting" if n_meet == 1 else f"{n_meet} meetings"
        st.markdown(
            "<div class='investor-group-title ff-anim-rise'>"
            f"{html.escape(name)} ({html.escape(label)})"
            "</div>",
            unsafe_allow_html=True,
        )
        pin_l, pin_r = st.columns(2)
        for idx, item in enumerate(items):
            fp = memory_fingerprint(item)
            row_key = f"{name}_{idx}_{fp}"
            col = pin_l if idx % 2 == 0 else pin_r
            with col:
                st.markdown(
                    f'<div class="memory-card ff-memory-pin ff-stagger-{idx % 6}">'
                    f"{_memory_meta_row_html(item)}"
                    f"<b>Notes:</b> {_html_multiline(item.get('notes', ''))}<br>"
                    f"<b>Objections:</b> {_html_multiline(item.get('objections', ''))}<br>"
                    f"<b>Promises:</b> {_html_multiline(item.get('promises', ''))}"
                    "</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Remove from store",
                    key=f"del_mem_{row_key}",
                    type="secondary",
                    use_container_width=True,
                ):
                    memory_store.delete_memory(item)
                    if hasattr(st, "toast"):
                        st.toast("Memory removed.")
                    st.rerun()


def _display_name_for_query(raw_query: str, memories: List[Dict]) -> str:
    if memories:
        return memories[-1].get("investor_name") or normalize_investor_name(raw_query)
    return normalize_investor_name(raw_query) if raw_query.strip() else raw_query


def _fallback_prepare(memories: List[Dict], investor_name: str) -> str:
    if not memories:
        return (
            "Last Meeting Summary:\n"
            f"No prior meeting with {investor_name} in memory.\n\n"
            "Key Concerns:\nUnknown until first conversation is logged.\n\n"
            "Pending Promises:\nNone captured.\n\n"
            "Suggested Talking Points:\n"
            "- Anchor on traction, team, and market clarity.\n"
            "- Offer to share deck and metrics proactively.\n\n"
            "Risks:\nInvestor may lack context without prior notes.\n\n"
            "Recommended Closing Strategy:\n"
            "Propose a concrete next step (data room, follow-up call, intro)."
        )

    latest = memories[-1]
    prior = memories[:-1]
    concerns = latest.get("objections", "None noted.") or "None noted."
    prom = latest.get("promises", "None noted.") or "None noted."
    hist = (
        "Earlier: "
        + "; ".join(
            f"{p.get('date')}: {p.get('notes', '')[:80]}"
            for p in prior[-2:]
            if p.get("notes")
        )
        if prior
        else "Single meeting on record."
    )
    return (
        "Last Meeting Summary:\n"
        f"{latest.get('notes', 'No notes.')}\n"
        f"Context: {hist}\n\n"
        "Key Concerns:\n"
        f"{concerns}\n\n"
        "Pending Promises:\n"
        f"{prom}\n\n"
        "Suggested Talking Points:\n"
        "- Address the latest concern with data.\n"
        "- Close open promises from memory.\n"
        "- Show momentum since last touchpoint.\n\n"
        "Risks:\n"
        "- Unresolved promises erode trust.\n\n"
        "Recommended Closing Strategy:\n"
        "Confirm materials sent, propose specific date for next sync."
    )


def _consume_dashboard_flash() -> None:
    flash = st.session_state.get("ff_dashboard_flash")
    if not flash:
        return
    st.session_state.ff_dashboard_flash = None
    kind, msg = flash
    if kind == "success":
        st.success(msg)
    elif kind == "info":
        st.info(msg)
    elif kind == "error":
        st.error(msg)


all_memories = memory_store.list_all()
unique_investors = len(
    {m.get("investor_name") for m in all_memories if m.get("investor_name")}
)
pending_n = count_pending_promises(all_memories)

with st.sidebar:
    st.markdown(
        '<p class="ff-sidebar-brand">FounderFlow</p>'
        '<p class="ff-sidebar-tag">Investor memory workspace</p>',
        unsafe_allow_html=True,
    )
    nav = st.session_state.ff_nav_page
    st.caption("Pages")
    if st.button(
        "Overview",
        use_container_width=True,
        type="primary" if nav == "overview" else "secondary",
    ):
        st.session_state.ff_nav_page = "overview"
        st.rerun()
    if st.button(
        "Add meeting",
        use_container_width=True,
        type="primary" if nav == "add" else "secondary",
    ):
        st.session_state.ff_nav_page = "add"
        st.rerun()
    if st.button(
        "Prepare meeting",
        use_container_width=True,
        type="primary" if nav == "prepare" else "secondary",
    ):
        st.session_state.ff_nav_page = "prepare"
        st.rerun()
    if st.button(
        "Generate email",
        use_container_width=True,
        type="primary" if nav == "email" else "secondary",
    ):
        st.session_state.ff_nav_page = "email"
        st.rerun()
    if st.button(
        "Memory chat",
        use_container_width=True,
        type="primary" if nav == "chat" else "secondary",
    ):
        st.session_state.ff_nav_page = "chat"
        st.rerun()
    st.divider()
    st.caption("Store & demo")
    if st.button("Run judge demo", use_container_width=True):
        memory_store.replace_all(DEMO_DATA)
        st.session_state.prepare_investor = "Rahul Mehta"
        st.session_state.judge_banner = (
            "Demo ready. Use Rahul Mehta in Prepare meeting (left menu)."
        )
        st.session_state.email_draft = ""
        st.session_state.demo_fill_idx = 0
        st.session_state.clear_add_form_after_save = True
        st.session_state.ff_nav_page = "prepare"
        st.rerun()
    if st.button("Load demo data", use_container_width=True):
        n = memory_store.append_demo_records(DEMO_DATA)
        if n:
            st.session_state.ff_dashboard_flash = (
                "success",
                f"Added {n} demo meeting(s) to the store. Open Add meeting and use Load next sample into form if you want the capture fields filled.",
            )
        else:
            st.session_state.ff_dashboard_flash = (
                "info",
                "All demo rows are already in memory. Use Add meeting → Load next sample into form, or Run judge demo to reload the canonical demo set.",
            )
        st.rerun()
    if st.button("Clear all memories", use_container_width=True):
        memory_store.clear_all()
        st.session_state.email_draft = ""
        st.session_state.demo_fill_idx = 0
        st.session_state.clear_add_form_after_save = True
        st.session_state.ff_dashboard_flash = ("success", "All local memories cleared.")
        st.rerun()
    if st.button(
        "Memory off / on",
        key="ff_memory_compare_toggle",
        use_container_width=True,
        help="Compare behavior without a meeting store vs with stored rows.",
    ):
        st.session_state.show_memory_compare = not st.session_state.show_memory_compare
        st.rerun()

_consume_dashboard_flash()

if st.session_state.judge_banner:
    st.success(st.session_state.judge_banner)
    st.caption(
        "Next: open Prepare meeting from the left menu, then Prepare Meeting Brief (Rahul Mehta is pre-filled)."
    )
    st.session_state.judge_banner = ""

page = st.session_state.ff_nav_page

if page == "overview":
    st.subheader("Executive overview")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.metric("Total memories", len(all_memories))
    with d2:
        st.metric("Unique investors", unique_investors)
    with d3:
        st.metric("Open promise items", pending_n)
    with d4:
        st.metric(
            "Memory file",
            "Local",
            help=f"Meetings are saved to `{memory_store.file_path}` on disk.",
        )

    st.caption(
        "Memory off / on (left sidebar): compare generic LLM output vs FounderFlow using your current store. "
        f"Run judge demo loads exactly {len(DEMO_DATA)} canonical demo rows; totals can grow if you save additional meetings."
    )

    if st.session_state.show_memory_compare:
        n_store = len(all_memories)
        store_status = (
            f"**Right now:** {n_store} row(s) in `{memory_store.file_path}`. "
            "While rows exist, **memory is on** for this session."
            if n_store
            else "**Right now:** the store is **empty**—load demo data or add a meeting so **memory on** uses real rows."
        )
        st.markdown("#### What changes with durable memory")
        st.markdown(store_status)
        off_c, on_c = st.columns(2)
        with off_c:
            st.markdown("##### Without durable memory")
            st.markdown(
                """
**What happens**

- **Prepare meeting** and **Generate email** only see text you paste in the same browser session—or the model guesses from the investor name alone.
- **No audit trail**: prior objections, promises, and meeting sequence are not tied to your last real call.
- **Memory chat** has nothing authoritative to quote; answers drift toward generic VC talk.

**User experience**

- You re-type context every time.
- Follow-ups can miss commitments you already made (“I’ll send the retention view”) because they were never stored.
                """.strip(),
            )
        with on_c:
            st.markdown("##### With memory on (FounderFlow)")
            st.markdown(
                """
**What happens**

- **Prepare meeting** builds a brief from **saved rows** for that investor (notes, objections, promises, dates).
- **Generate email** uses the **same** store so tone and facts line up with what was logged.
- **Memory chat** reads a structured export (timeline + per-investor “#1 = most recent”) so you can ask for “last three meetings with Rahul” and get grounded answers.

**User experience**

- One place to log what was said; prep and outbound stay aligned with that history.
- **Local JSON** on disk is the source of truth for this app.
                """.strip(),
            )

    insight_lines = _founder_insights(all_memories)
    st.markdown(
        '<p class="ff-insight-board-title">AI founder insights</p>',
        unsafe_allow_html=True,
    )
    if insight_lines:
        ins_l, ins_r = st.columns(2)
        for i, line in enumerate(insight_lines):
            inner = _insight_line_to_html(line)
            col = ins_l if i % 2 == 0 else ins_r
            with col:
                st.markdown(
                    f'<div class="ff-insight-pin ff-stagger-{i % 6}">'
                    f'<div class="ff-insight-body">'
                    f'<span class="ff-bullet">•</span>{inner}'
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
    st.markdown("")

    with st.expander("Why Memory Wins"):
        st.markdown(
            """
**Without Memory:**  
"Pitch confidently."

**With FounderFlow:**  
"Rahul asked CAC twice and still awaits your retention dashboard."
            """
        )

    with st.expander("Why persistent memory matters"):
        st.markdown(
            """
**Without chat memory:** each LLM session forgets your investors and promises.

**With FounderFlow:** notes, objections, and tasks stay in **durable memory** on disk—prep and email pull the **same** relationship context every time.
            """
        )

elif page == "add":
    if st.session_state.clear_add_form_after_save:
        st.session_state.add_form_investor = ""
        st.session_state.add_form_notes = ""
        st.session_state.add_form_objections = ""
        st.session_state.add_form_promises = ""
        st.session_state.clear_add_form_after_save = False

    st.subheader("Add Investor Meeting Memory")
    if st.session_state.save_meeting_flash:
        st.success(st.session_state.save_meeting_flash)
        st.session_state.save_meeting_flash = None
    before_count = len(memory_store.list_all())
    st.caption(f"Memories before save: {before_count}")
    st.caption(
        "**Load next sample into form** pulls one demo row into these fields. "
        "**Load demo data** (left sidebar) only fills the memory store—fields stay empty until you load a sample here or type your own notes, then **Save Memory**."
    )

    sf1, sf2 = st.columns(2)
    with sf1:
        if st.button("Load next sample into form", use_container_width=True):
            idx = st.session_state.demo_fill_idx % len(DEMO_DATA)
            _apply_demo_row_to_add_form(DEMO_DATA[idx])
            st.session_state.demo_fill_idx = idx + 1
            st.success("Form filled from demo—switch fields as needed, then Save.")
            st.rerun()
    with sf2:
        if st.button("Clear form fields", use_container_width=True):
            st.session_state.add_form_investor = ""
            st.session_state.add_form_notes = ""
            st.session_state.add_form_objections = ""
            st.session_state.add_form_promises = ""
            st.rerun()

    # Not using st.form: form widgets defer session_state updates until submit, which breaks
    # programmatic fills from "Load demo data" / "Load next sample" (same keys, no submit).
    with st.container(border=True):
        st.markdown(
            '<div class="ff-meeting-head">'
            '<p class="ff-meeting-head-title">Meeting capture</p>'
            '<span class="ff-meeting-ready">'
            '<span class="ff-meeting-ready-dot" aria-hidden="true"></span>Ready'
            "</span></div>",
            unsafe_allow_html=True,
        )
        st.text_input(
            "Investor Name",
            placeholder="e.g. Rahul Mehta (empty until you load a sample or type)",
            key="add_form_investor",
        )
        st.text_area(
            "Meeting Notes",
            placeholder="Use Load next sample or Load demo data to fill, or type your own…",
            key="add_form_notes",
            height=100,
        )
        st.text_area(
            "Objections",
            placeholder="Objections / concerns (optional)",
            key="add_form_objections",
            height=80,
        )
        st.text_area(
            "Promises / Tasks",
            placeholder="Follow-ups you committed to (optional)",
            key="add_form_promises",
            height=80,
        )
        submitted = st.button("Save Memory", type="primary", use_container_width=True)

    if submitted:
        inv = st.session_state.add_form_investor.strip()
        nt = st.session_state.add_form_notes.strip()
        ob = st.session_state.add_form_objections.strip()
        pr = st.session_state.add_form_promises.strip()
        if not inv or not nt:
            st.error("Investor Name and Meeting Notes are required.")
        else:
            record = {
                "investor_name": inv,
                "notes": nt,
                "objections": ob,
                "promises": pr,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            result = memory_store.save_memory(record)
            after_count = len(memory_store.list_all())
            if result.get("duplicate"):
                st.session_state.save_meeting_flash = (
                    "That meeting is **already in memory** (same investor, date, notes, objections, promises). "
                    "Nothing was added—edit the form or change the date if you meant a new meeting."
                )
            else:
                st.session_state.clear_add_form_after_save = True
                st.session_state.save_meeting_flash = (
                    f"Memory saved ({after_count} total) to `{memory_store.file_path}`."
                )
            st.rerun()

    st.markdown("### Current Memory Store")
    _render_memory_cards_grouped(memory_store.list_all())

elif page == "prepare":
    st.subheader("Prepare for Next Investor Meeting")
    prep_investor = st.text_input(
        "Investor Name",
        key="prepare_investor",
        placeholder="Try Rahul Mehta — partial names work",
    )

    if st.button("Prepare Meeting Brief", type="primary"):
        if not prep_investor.strip():
            st.error("Please enter an investor name.")
        else:
            memories = memory_store.get_memories_for_investor(prep_investor.strip())
            display_name = _display_name_for_query(prep_investor.strip(), memories)
            context = memories_to_text(memories)
            prompt = build_prepare_meeting_prompt(display_name, context)
            ai_response = llm_client.complete(prompt)
            fb = _fallback_prepare(memories, display_name)

            if memories:
                st.markdown("### Investor memory timeline")
                _render_timeline_newest_first(memories)
                st.divider()

            st.markdown("### Investor Memory Context")
            st.code(context)

            st.markdown("### Preparation brief")
            if "missing" in ai_response.lower() or "failed" in ai_response.lower():
                st.warning(ai_response)
                _render_prep_cards(fb, fb)
            else:
                _render_prep_cards(ai_response, fb)

elif page == "email":
    st.subheader("Generate Investor Follow-up Email")
    email_investor = st.text_input(
        "Investor Name",
        key="email_investor",
        placeholder="Investor name (partial match OK)",
    )
    tone = st.selectbox(
        "Tone",
        ["Professional", "Friendly", "Investor Formal"],
        key="email_tone",
    )

    gc1, gc2 = st.columns(2)
    with gc1:
        gen_email = st.button("Generate Follow-up Email", type="primary")
    with gc2:
        regen_email = st.button("Regenerate")

    if gen_email or regen_email:
        if not email_investor.strip():
            st.error("Please enter an investor name.")
        else:
            memories = memory_store.get_memories_for_investor(email_investor.strip())
            display_name = _display_name_for_query(email_investor.strip(), memories)
            context = memories_to_text(memories)
            prompt = build_email_prompt(display_name, context, tone=tone)
            email_text = llm_client.complete(prompt, temperature=0.4)
            st.session_state.email_draft = email_text

    draft = st.session_state.get("email_draft", "")
    if draft:
        inv = st.session_state.email_investor.strip()
        memories = memory_store.get_memories_for_investor(inv) if inv else []
        display_ctx = _display_name_for_query(inv, memories) if inv else "Investor"

        st.markdown("### Investor Memory Context")
        st.code(memories_to_text(memories) if memories else "No prior meetings found.")

        st.markdown("### Draft Email")
        low = draft.lower()
        show_draft = draft
        if "missing" in low or "failed" in low:
            st.warning(draft)
            show_draft = (
                f"Subject: Follow-up from our meeting, {display_ctx}\n\n"
                f"Hi {display_ctx},\n\n"
                "Thank you for your time in our recent meeting. I appreciated your candid feedback "
                "and questions.\n\n"
                "As discussed, I am sharing the requested materials and key updates. Please let me know "
                "if you would like a deeper breakdown before our next call.\n\n"
                "Would next week work for a 20-minute follow-up?\n\n"
                "Best regards,\nFounder"
            )
            st.session_state.email_draft = show_draft

        st.text(show_draft)
        subj, body_only = parse_email_subject_body(show_draft)
        gmail_u = gmail_compose_url(subj, body_only)
        mail_u = mailto_url(subj, body_only)

        st.markdown("##### Actions")
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if st.button(
                "Copy email",
                use_container_width=True,
                type="primary",
                key="ff_email_action_copy",
            ):
                try:
                    import pyperclip

                    pyperclip.copy(show_draft)
                    st.toast("Copied to clipboard.")
                except ImportError:
                    st.info(
                        "One-click copy needs **`pyperclip`**: run `pip install pyperclip`, "
                        "or select the draft text above (**Ctrl+A**, **Ctrl+C**)."
                    )
                except Exception:
                    st.toast(
                        "Could not copy automatically — select the draft with Ctrl+A, Ctrl+C.",
                    )
        with ac2:
            st.link_button(
                "Open in Gmail",
                gmail_u,
                use_container_width=True,
                help="Opens Gmail compose with subject & body (add recipient).",
            )
        with ac3:
            st.link_button(
                "Open in mail app",
                mail_u,
                use_container_width=True,
                help="Opens your default mail client (mailto:).",
            )
        st.caption(
            "Gmail and Mail use your parsed **Subject** and **body**. Add the **To** field, then send."
        )

elif page == "chat":
    st.subheader("Memory chat")
    st.caption(
        "Ask anything about saved meetings—e.g. **last three meetings with Rahul**, **what Priya said in her second most recent meeting**, "
        "open promises, or timelines. Answers use **saved memory only**."
    )
    c_clear, c_dummy = st.columns([1, 3])
    with c_clear:
        if st.button("Clear chat history", key="ff_chat_clear"):
            st.session_state.chat_messages = []
            st.session_state._memory_chat_pending = False
            st.rerun()

    # Two-step flow: append user + rerun, then answer on next run (reliable with st.chat_input).
    msgs: List[Dict[str, str]] = st.session_state.chat_messages
    if st.session_state._memory_chat_pending:
        if msgs and msgs[-1].get("role") == "user":
            user_text = str(msgs[-1].get("content", "")).strip()
            dump = _memory_dump_for_chat()
            try:
                with st.spinner("Generating answer from memory…"):
                    if not memory_store.list_all():
                        reply = (
                            "There are **no meetings in memory** yet. Add some under **Add meeting**, "
                            "or use **Load demo data** in the left sidebar."
                        )
                    else:
                        raw = llm_client.complete(
                            build_memory_chat_user_prompt(dump, user_text),
                            temperature=0.35,
                            system_prompt=MEMORY_CHAT_SYSTEM,
                        )
                        reply = (raw or "").strip() or "No response was returned."
            except Exception as exc:
                reply = f"Could not complete the request: {exc}"
            st.session_state.chat_messages.append({"role": "assistant", "content": reply})
        st.session_state._memory_chat_pending = False
        st.rerun()

    for msg in st.session_state.chat_messages:
        role = msg.get("role", "assistant")
        if role not in ("user", "assistant", "system"):
            role = "assistant"
        with st.chat_message(role):
            st.markdown(str(msg.get("content", "")))

    chat_prompt = st.chat_input(
        "Ask about investors, last N meetings, or a specific meeting…",
        key="ff_memory_chat_input",
    )
    if chat_prompt:
        st.session_state.chat_messages.append(
            {"role": "user", "content": str(chat_prompt).strip()}
        )
        st.session_state._memory_chat_pending = True
        st.rerun()

# st.chat_input must stay the last main-area widget on Memory chat runs; anything
# rendered after it breaks submit / sticky behavior (Streamlit pins chat to bottom).
if page != "chat":
    st.markdown("---")
    st.caption(
        "Tip: set `GROQ_API_KEY` in `.env` for AI features. Meeting data is stored locally in `memory_store.json`."
    )
    st.markdown(
        "<div class='ff-footer'>"
        "<span style='opacity:0.92'>FounderFlow AI — memory-powered founder OS</span>"
        "</div>",
        unsafe_allow_html=True,
    )
