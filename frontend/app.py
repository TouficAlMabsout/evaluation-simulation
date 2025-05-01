import streamlit as st
import requests
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize mock session data if not already set
if "conversations" not in st.session_state:
    st.session_state.conversations = [
        {
            "conversation_id": "1234",
            "username": "bob",
            "date_of_report": "2025-05-01 12:30",
            "content": [
                {"role": "human", "content": "hello"},
                {"role": "ai", "content": ""},
                {"role": "human", "content": "I want a visa"},
                {"role": "ai", "content": ""}
            ],
            "results": []
        },
        {
            "conversation_id": "5678",
            "username": "alice",
            "date_of_report": "2025-05-01 14:00",
            "content": [
                {"role": "human", "content": "hi"},
                {"role": "ai", "content": ""},
                {"role": "human", "content": "can you help me with something?"},
                {"role": "ai", "content": ""}
            ],
            "results": []
        }
    ]

if "open_analyze_id" not in st.session_state:
    st.session_state.open_analyze_id = None


@st.cache_data(show_spinner=False)
def fetch_prompt_list_from_api():
    try:
        res = requests.get("http://localhost:8000/prompts")
        if res.status_code == 200:
            return res.json()
        else:
            st.warning("Could not fetch prompts from server.")
            return []
    except Exception as e:
        st.error(f"Error fetching prompts: {e}")
        return []

def get_prompt_variables(prompt_id):
    try:
        res = requests.get("http://localhost:8000/prompt-variables", params={"prompt_id": prompt_id})
        if res.status_code == 200:
            return res.json().get("variables", [])
        else:
            return []
    except Exception as e:
        st.error(f"Failed to fetch prompt variables: {e}")
        return []

from math import ceil

st.title("Evaluation Dashboard")

conversations = st.session_state.conversations

if "open_analysis_id" not in st.session_state:
    st.session_state.open_analysis_id = None

per_page = 5
total_pages = ceil(len(conversations) / per_page)

if "current_page" not in st.session_state:
    st.session_state.current_page = 1

col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("◀ Prev") and st.session_state.current_page > 1:
        st.session_state.current_page -= 1
with col3:
    if st.button("Next ▶") and st.session_state.current_page < total_pages:
        st.session_state.current_page += 1

col2.markdown(f"<div style='text-align: center;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)

page = st.session_state.current_page


start = (page - 1) * per_page
end = start + per_page
displayed = conversations[start:end]
header_cols = st.columns([2, 2, 2, 2, 2])

header_cols[0].markdown("**Username**")
header_cols[1].markdown("**Date & Time**")
header_cols[2].markdown("**Conversation ID**")
header_cols[3].markdown("**View Past Analysis**")
header_cols[4].markdown("**Analyze**")

for convo in displayed:
    cols = st.columns([2, 2, 2, 2, 2])
    cols[0].write(convo["username"])
    cols[1].write(convo["date_of_report"])
    cols[2].write(convo["conversation_id"])

    # View Past Analysis
    if cols[3].button("View", key=f"view_{convo['conversation_id']}"):
        if st.session_state.open_analysis_id == convo["conversation_id"]:
            st.session_state.open_analysis_id = None  # Toggle off
        else:
            st.session_state.open_analysis_id = convo["conversation_id"]

    if st.session_state.open_analysis_id == convo["conversation_id"]:
        st.subheader(f"Past Analysis - {convo['conversation_id']}")
        if convo["results"]:
            for res in convo["results"]:
                st.markdown(f"- **Time**: {res['time']}  \n"
                            f"**Prompt ID**: `{res['prompt_id']}`  \n"
                            f"**Model**: `{res['model']}`  \n"
                            f"**Variables**: `{json.dumps(res['variables'])}`")
                for m in res["output"]:
                    st.markdown(f"**{m['role']}**: {m['content']}")
                st.markdown("---")
        else:
            st.info("No analysis has been performed yet.")


    if cols[4].button("Analyze", key=f"analyze_{convo['conversation_id']}"):
        if st.session_state.open_analyze_id == convo["conversation_id"]:
            st.session_state.open_analyze_id = None  # Toggle off
        else:
            st.session_state.open_analyze_id = convo["conversation_id"]
    
    if st.session_state.open_analyze_id == convo["conversation_id"]:
        st.markdown("---")
        st.subheader(f"New Analysis - {convo['conversation_id']}")

        # Fetch prompt list
        all_prompts = fetch_prompt_list_from_api()

        selected_prompt = st.selectbox(
            "Select Prompt (type to search)",
            options=[""] + all_prompts,  # blank placeholder
            key=f"prompt_select_{convo['conversation_id']}"
        )



        selected_model = st.selectbox("Select Claude Model", [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229"
        ], key=f"model_select_{convo['conversation_id']}")

        variable_values = {}

        # Only fetch variables when user selects a valid prompt (not the blank one)
        if selected_prompt and selected_prompt.strip() != "":
            input_variables = get_prompt_variables(selected_prompt)

            if input_variables:
                st.markdown("**Optional Variables:**")
                for var in input_variables:
                    val = st.text_input(f"{var} (optional)", key=f"{convo['conversation_id']}_{var}")
                    variable_values[var] = val if val.strip() else "missing"



        st.button("Run Analysis", key=f"run_{convo['conversation_id']}")


