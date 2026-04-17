import html
import os
import re
import urllib.parse
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

import streamlit as st
from dotenv import load_dotenv

from llm import GroqClient
from memory import (
    DEMO_DATA,
    check_hindsight_connection,
    count_pending_promises,
    create_store_from_env,
    memories_to_text,
    memory_fingerprint,
    normalize_investor_name,
)
from prompts import (
    PREP_SECTION_HEADERS,
    build_email_prompt,
    build_prepare_meeting_prompt,
)


load_dotenv()

st.set_page_config(page_title="FounderFlow AI", page_icon="🚀", layout="wide")

st.markdown(
    """
    <style>
        .main .block-container {
            padding-top: 1.35rem;
            padding-bottom: 2.75rem;
            max-width: 1120px;
        }
        .ff-hero {
            margin-bottom: 0.35rem;
        }
        .app-subtitle {
            color: var(--gray-70, #94a3b8);
            margin-top: -6px;
            margin-bottom: 1.35rem;
            font-size: 1.12rem;
            font-weight: 500;
        }
        .dash-panel {
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 16px;
            padding: 1.1rem 1.25rem 1.25rem 1.25rem;
            margin-bottom: 1.15rem;
            background: var(--secondary-background-color, rgba(99, 102, 241, 0.06));
        }
        .insights-panel {
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 16px;
            padding: 1rem 1.2rem;
            margin: 1rem 0 1.2rem 0;
            background: linear-gradient(
                135deg,
                rgba(99, 102, 241, 0.08) 0%,
                rgba(14, 165, 233, 0.06) 100%
            );
        }
        .insights-panel h4 {
            margin: 0 0 0.65rem 0;
            font-size: 1.05rem;
        }
        .memory-card {
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.65rem;
            background-color: var(--secondary-background-color, rgba(128, 128, 128, 0.08));
            box-shadow: none;
        }
        .prep-section-card {
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 14px;
            padding: 1rem 1.15rem;
            margin-bottom: 0.75rem;
            background: var(--secondary-background-color, rgba(128, 128, 128, 0.06));
        }
        .timeline-rail {
            border-left: 3px solid rgba(99, 102, 241, 0.55);
            margin-left: 10px;
            padding-left: 1.15rem;
        }
        .timeline-dot {
            width: 11px;
            height: 11px;
            border-radius: 50%;
            background: #6366f1;
            margin-left: -19px;
            margin-top: 6px;
            float: left;
        }
        .investor-group-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-color, #0f172a);
            margin: 1.25rem 0 0.5rem 0;
        }
        .small-muted {
            color: var(--gray-70, #94a3b8);
            font-size: 0.9rem;
        }
        div[data-testid="stExpander"] details {
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.28);
            background: transparent !important;
        }
        div[data-testid="stExpander"] summary {
            color: var(--text-color);
        }
        h3 { letter-spacing: -0.02em; }
        [data-testid="stMetric"] {
            background: var(--secondary-background-color, rgba(0,0,0,0.04));
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 12px;
            padding: 0.65rem 0.75rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚀 FounderFlow AI")
st.markdown(
    '<div class="app-subtitle">Memory-Powered Founder OS · Built for founders who close rounds</div>',
    unsafe_allow_html=True,
)

memory_store = create_store_from_env()
llm_client = GroqClient()

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


@st.cache_data(ttl=90)
def _cached_hindsight_live(api_key: str) -> bool:
    return check_hindsight_connection(api_key)


def _hindsight_status_label() -> str:
    key = os.getenv("HINDSIGHT_API_KEY", "").strip()
    if not key:
        return "Local Fallback"
    return "Connected" if _cached_hindsight_live(key) else "Local Fallback"


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
    for m in ordered:
        notes = m.get("notes", "") or "—"
        obj = m.get("objections", "") or "—"
        prom = m.get("promises", "") or "—"
        st.markdown(
            f'<div class="memory-card" style="border-left: 4px solid #6366f1;">'
            f"<strong>📍 {m.get('date', '—')}</strong>"
            f"<span class='small-muted'> · Meeting</span><br><br>"
            f"<b>Notes:</b> {notes}<br>"
            f"<b>Concerns:</b> {obj}<br>"
            f"<b>Promises:</b> {prom}"
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
            "📊 **Rahul Mehta** repeatedly presses **efficiency metrics** (CAC, burn)—lead with crisp numbers."
        )
    elif rahul and eff_hits:
        insights.append(
            "📊 **Rahul Mehta** is focused on **efficiency and unit economics** in your narrative."
        )

    priya = by_name.get("Priya Sharma", [])
    priya_blob = " ".join(
        f"{m.get('notes', '')} {m.get('objections', '')}" for m in priya
    ).lower()
    if "revenue" in priya_blob or "predictability" in priya_blob:
        insights.append(
            "📈 **Priya Sharma** cares about **revenue predictability** and **GTM depth**—tie partnerships to pipeline."
        )

    pending = count_pending_promises(rows)
    if pending >= 3:
        insights.append(
            f"✅ **{pending} logged follow-ups** still have promises attached—close the loop before the next call."
        )
    elif pending:
        insights.append(
            f"✅ **{pending} meeting(s)** include open promises—review before you pitch again."
        )

    ret_n = sum(
        1
        for m in rows
        if "retention" in f"{m.get('notes', '')} {m.get('objections', '')}".lower()
    )
    if ret_n >= 2:
        insights.append(
            "🔁 **Retention** shows up multiple times—prepare cohort charts and a clear story."
        )
    elif ret_n == 1:
        insights.append(
            "🔁 **Retention** has surfaced—have one sharp proof point ready."
        )

    if not insights:
        insights.append(
            "💡 Patterns will appear as you add objections, promises, and richer notes."
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
            f'<div class="investor-group-title">{name} ({label})</div>',
            unsafe_allow_html=True,
        )
        for idx, item in enumerate(items):
            fp = memory_fingerprint(item)
            row_key = f"{name}_{idx}_{fp}"
            c_body, c_del = st.columns([4.2, 1])
            with c_body:
                st.markdown(
                    (
                        '<div class="memory-card">'
                        f"<span class='small-muted'>{item.get('date', 'unknown')}</span><br><br>"
                        f"<b>Notes:</b> {item.get('notes', '')}<br>"
                        f"<b>Objections:</b> {item.get('objections', '')}<br>"
                        f"<b>Promises:</b> {item.get('promises', '')}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
            with c_del:
                st.write("")
                if st.button(
                    "Delete",
                    key=f"del_mem_{row_key}",
                    type="secondary",
                    use_container_width=True,
                ):
                    memory_store.delete_memory(item)
                    if hasattr(st, "toast"):
                        st.toast("Memory removed.", icon="🗑️")
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


all_memories = memory_store.list_all()
unique_investors = len(
    {m.get("investor_name") for m in all_memories if m.get("investor_name")}
)
pending_n = count_pending_promises(all_memories)

st.caption("Founder dashboard")
d1, d2, d3, d4 = st.columns(4)
with d1:
    st.metric("📚 Total Memories", len(all_memories))
with d2:
    st.metric("👤 Unique Investors", unique_investors)
with d3:
    st.metric("📌 Pending Promises", pending_n)
with d4:
    st.metric("☁️ Memory Status", _hindsight_status_label())

r1, r2, r3, r4 = st.columns(4)
with r1:
    if st.button("🚀 Run Judge Demo", use_container_width=True, type="primary"):
        memory_store.replace_all(DEMO_DATA)
        st.session_state.prepare_investor = "Rahul Mehta"
        st.session_state.judge_banner = (
            "Demo ready. Use Rahul Mehta in Prepare Meeting."
        )
        st.session_state.email_draft = ""
        st.rerun()
with r2:
    if st.button("Load Demo Data", use_container_width=True):
        n = memory_store.append_demo_records(DEMO_DATA)
        if n:
            st.success(f"Added {n} new demo meeting(s) (duplicates skipped).")
        else:
            st.info("All demo meetings already in memory.")
        st.rerun()
with r3:
    if st.button("Reset All Demo Data", use_container_width=True):
        memory_store.replace_all(DEMO_DATA)
        st.session_state.email_draft = ""
        st.success("Memory replaced with full demo timeline.")
        st.rerun()
with r4:
    if st.button("Clear All Memories", use_container_width=True):
        memory_store.clear_all()
        st.session_state.email_draft = ""
        st.success("All local memories cleared.")
        st.rerun()

if st.session_state.judge_banner:
    st.success(st.session_state.judge_banner)
    st.caption(
        "Next: open **🎯 Prepare Meeting** → **Prepare Meeting Brief** (Rahul is pre-filled)."
    )
    st.session_state.judge_banner = ""

insight_lines = _founder_insights(all_memories)
st.markdown("#### ✨ AI Founder Insights")
for line in insight_lines:
    st.markdown(f"- {line}")
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

**With FounderFlow:** notes, objections, and tasks stay in **durable memory** (local + Hindsight when connected)—prep and email pull the **same** relationship context every time.
        """
    )

tab_add, tab_prepare, tab_email = st.tabs(
    ["📝 Add Meeting", "🎯 Prepare Meeting", "✉️ Generate Email"]
)

with tab_add:
    st.subheader("Add Investor Meeting Memory")
    before_count = len(memory_store.list_all())
    st.caption(f"Memories before save: {before_count}")

    with st.form("add_meeting_form", clear_on_submit=True):
        investor_name = st.text_input("Investor Name", placeholder="Rahul Mehta")
        notes = st.text_area(
            "Meeting Notes", placeholder="Asked CAC and growth metrics..."
        )
        objections = st.text_area("Objections", placeholder="High CAC concerns...")
        promises = st.text_area(
            "Promises / Tasks", placeholder="Send updated pitch deck..."
        )
        submitted = st.form_submit_button("Save Memory")

    if submitted:
        if not investor_name.strip() or not notes.strip():
            st.error("Investor Name and Meeting Notes are required.")
        else:
            record = {
                "investor_name": investor_name.strip(),
                "notes": notes.strip(),
                "objections": objections.strip(),
                "promises": promises.strip(),
                "date": datetime.now().strftime("%Y-%m-%d"),
            }
            result = memory_store.save_memory(record)
            after_count = len(memory_store.list_all())
            st.success(
                "✅ Memory saved successfully and available for future investor prep."
            )
            st.caption(f"Memories after save: {after_count}")
            st.write(
                {
                    "local_saved": result["local_saved"],
                    "hindsight_saved": result["hindsight_saved"],
                }
            )

    st.markdown("### Current Memory Store")
    _render_memory_cards_grouped(memory_store.list_all())

with tab_prepare:
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
                st.markdown("### 📅 Investor memory timeline")
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

with tab_email:
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

        st.markdown("##### ✉️ Actions")
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if st.button(
                "📋 Copy Email",
                use_container_width=True,
                type="primary",
                key="ff_email_action_copy",
            ):
                try:
                    import pyperclip

                    pyperclip.copy(show_draft)
                    st.toast("Copied to clipboard!", icon="✅")
                except ImportError:
                    st.info(
                        "One-click copy needs **`pyperclip`**: run `pip install pyperclip`, "
                        "or select the draft text above (**Ctrl+A**, **Ctrl+C**)."
                    )
                except Exception:
                    st.toast(
                        "Could not copy automatically — select the draft with Ctrl+A, Ctrl+C.",
                        icon="⚠️",
                    )
        with ac2:
            st.link_button(
                "📧 Open in Gmail",
                gmail_u,
                use_container_width=True,
                help="Opens Gmail compose with subject & body (add recipient).",
            )
        with ac3:
            st.link_button(
                "✉️ Open in Mail App",
                mail_u,
                use_container_width=True,
                help="Opens your default mail client (mailto:).",
            )
        st.caption(
            "Gmail and Mail use your parsed **Subject** and **body**. Add the **To** field, then send."
        )

st.markdown("---")
st.caption(
    "Tip: set `GROQ_API_KEY` and `HINDSIGHT_API_KEY` in `.env` (see `.env.example`). "
    "Local memory always works for demos."
)
st.markdown(
    "<div style='text-align:center;color:#64748b;font-size:0.92rem;line-height:1.6;padding:10px 0 0 0;'>"
    "Built for Hindsight Hackathon 🚀<br>"
    "<span style='opacity:0.9'>FounderFlow AI – Memory Powered Founder OS</span>"
    "</div>",
    unsafe_allow_html=True,
)
