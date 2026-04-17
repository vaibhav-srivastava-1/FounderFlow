from datetime import datetime
from typing import Dict, List

import streamlit as st
from dotenv import load_dotenv

from llm import GroqClient
from memory import create_store_from_env, memories_to_text
from prompts import build_email_prompt, build_prepare_meeting_prompt


load_dotenv()

st.set_page_config(page_title="FounderFlow AI", page_icon="🚀", layout="wide")

st.markdown(
    """
    <style>
        .main {
            padding-top: 1rem;
        }
        .app-subtitle {
            color: #6b7280;
            margin-top: -10px;
            margin-bottom: 20px;
            font-size: 1.1rem;
        }
        .memory-card {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 10px;
            background: #fafafa;
        }
        .small-muted {
            color: #6b7280;
            font-size: 0.9rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚀 FounderFlow AI")
st.markdown('<div class="app-subtitle">Memory-Powered Founder Assistant</div>', unsafe_allow_html=True)

memory_store = create_store_from_env()
llm_client = GroqClient()


def _render_memory_cards(memories: List[Dict]) -> None:
    if not memories:
        st.info("No meeting memories found yet.")
        return

    for item in reversed(memories):
        st.markdown(
            (
                '<div class="memory-card">'
                f"<b>{item.get('investor_name', 'Unknown Investor')}</b> "
                f"<span class='small-muted'>({item.get('date', 'unknown')})</span><br><br>"
                f"<b>Notes:</b> {item.get('notes', '')}<br>"
                f"<b>Objections:</b> {item.get('objections', '')}<br>"
                f"<b>Promises:</b> {item.get('promises', '')}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def _fallback_prepare(memories: List[Dict], investor_name: str) -> str:
    if not memories:
        return (
            f"Last meeting summary:\nNo previous meeting with {investor_name} found.\n\n"
            "Investor objections:\nNo objections captured.\n\n"
            "Pending promises:\nNo pending promises.\n\n"
            "Suggested talking points:\n- Reintroduce startup progress since last update.\n"
            "- Share top metrics (revenue, growth, CAC/LTV).\n\n"
            "Risks:\n- Limited context may reduce investor confidence.\n\n"
            "Next actions:\n- Capture detailed notes after the next call."
        )

    latest = memories[-1]
    return (
        "Last meeting summary:\n"
        f"{latest.get('notes', 'No notes captured.')}\n\n"
        "Investor objections:\n"
        f"{latest.get('objections', 'No objections captured.')}\n\n"
        "Pending promises:\n"
        f"{latest.get('promises', 'No promises captured.')}\n\n"
        "Suggested talking points:\n"
        "- Show improved CAC trend and efficiency gains.\n"
        "- Present latest revenue or traction movement.\n"
        "- Address concern directly with proof points.\n\n"
        "Risks:\n"
        "- If promises remain open, trust may reduce.\n"
        "- Weak metric clarity may delay decision.\n\n"
        "Next actions:\n"
        "- Send promised materials within 24 hours.\n"
        "- Propose next meeting date and agenda."
    )


tab_add, tab_prepare, tab_email = st.tabs(
    ["Add Meeting", "Prepare Meeting", "Generate Email"]
)

with tab_add:
    st.subheader("Add Investor Meeting Memory")
    before_count = len(memory_store.list_all())
    st.caption(f"Memories before save: {before_count}")

    with st.form("add_meeting_form", clear_on_submit=True):
        investor_name = st.text_input("Investor Name", placeholder="Rahul Mehta")
        notes = st.text_area("Meeting Notes", placeholder="Asked CAC and growth metrics...")
        objections = st.text_area("Objections", placeholder="High CAC concerns...")
        promises = st.text_area("Promises / Tasks", placeholder="Send updated pitch deck...")
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
            st.success("Meeting memory saved successfully.")
            st.caption(f"Memories after save: {after_count}")
            st.write(
                {
                    "local_saved": result["local_saved"],
                    "hindsight_saved": result["hindsight_saved"],
                }
            )

    st.markdown("### Current Memory Store")
    _render_memory_cards(memory_store.list_all())

with tab_prepare:
    st.subheader("Prepare for Next Investor Meeting")
    prep_investor = st.text_input(
        "Investor Name",
        key="prepare_investor",
        placeholder="Enter investor name to prepare for meeting",
    )

    if st.button("Prepare Meeting Brief", type="primary"):
        if not prep_investor.strip():
            st.error("Please enter an investor name.")
        else:
            memories = memory_store.get_memories_for_investor(prep_investor.strip())
            context = memories_to_text(memories)
            prompt = build_prepare_meeting_prompt(prep_investor.strip(), context)
            ai_response = llm_client.complete(prompt)

            st.markdown("### Investor Memory Context")
            st.code(context)

            st.markdown("### Preparation Brief")
            if "missing" in ai_response.lower() or "failed" in ai_response.lower():
                st.warning(ai_response)
                st.text(_fallback_prepare(memories, prep_investor.strip()))
            else:
                st.text(ai_response)

with tab_email:
    st.subheader("Generate Investor Follow-up Email")
    email_investor = st.text_input(
        "Investor Name",
        key="email_investor",
        placeholder="Enter investor name for follow-up email",
    )

    if st.button("Generate Follow-up Email"):
        if not email_investor.strip():
            st.error("Please enter an investor name.")
        else:
            memories = memory_store.get_memories_for_investor(email_investor.strip())
            context = memories_to_text(memories)
            prompt = build_email_prompt(email_investor.strip(), context)
            email_text = llm_client.complete(prompt, temperature=0.4)

            st.markdown("### Investor Memory Context")
            st.code(context)

            st.markdown("### Draft Email")
            if "missing" in email_text.lower() or "failed" in email_text.lower():
                st.warning(email_text)
                st.text(
                    (
                        f"Subject: Follow-up from our meeting, {email_investor.strip()}\n\n"
                        f"Hi {email_investor.strip()},\n\n"
                        "Thank you for your time in our recent meeting. I appreciated your candid feedback "
                        "and questions.\n\n"
                        "As discussed, I am sharing the requested materials and key updates. Please let me know "
                        "if you would like a deeper breakdown before our next call.\n\n"
                        "Would next week work for a 20-minute follow-up?\n\n"
                        "Best regards,\nFounder"
                    )
                )
            else:
                st.text(email_text)

st.caption(
    "Tip: Add your GROQ_API_KEY and HINDSIGHT_API_KEY in .env. "
    "If APIs are unavailable, local memory fallback keeps demo fully functional."
)
