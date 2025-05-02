# app.py
import streamlit as st
import requests
from dotenv import load_dotenv
import json
from datetime import datetime
from math import ceil
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data_store import load_conversations, save_single_conversation

# Load environment variables
load_dotenv()

# Init session state
if "conversations" not in st.session_state:
    st.session_state.conversations = load_conversations()

if "open_analyze_id" not in st.session_state:
    st.session_state.open_analyze_id = None
if "open_view_id" not in st.session_state:
    st.session_state.open_view_id = None
if "prompt_cache" not in st.session_state:
    st.session_state.prompt_cache = {}

# API fetch functions
@st.cache_data(show_spinner=False)
def fetch_prompt_list():
    try:
        res = requests.get("http://localhost:8000/prompts")
        if res.status_code == 200:
            return res.json()
        else:
            return []
    except:
        return []

def fetch_prompt_variables(prompt_id):
    if prompt_id in st.session_state.prompt_cache:
        return st.session_state.prompt_cache[prompt_id]
    try:
        res = requests.get("http://localhost:8000/prompt-variables", params={"prompt_id": prompt_id})
        if res.status_code == 200:
            vars = res.json().get("variables", [])
            st.session_state.prompt_cache[prompt_id] = vars
            return vars
        else:
            return []
    except:
        return []

# UI
st.title("Evaluation Dashboard")
conversations = st.session_state.conversations
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
col2.markdown(f"<div style='text-align:center;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)

start = (st.session_state.current_page - 1) * per_page
end = start + per_page
displayed = conversations[start:end]

st.divider()
header_cols = st.columns([2, 2, 2, 2, 2])
header_cols[0].markdown("**Username**")
header_cols[1].markdown("**Date & Time**")
header_cols[2].markdown("**Conversation ID**")
header_cols[3].markdown("**Past Analysis**")
header_cols[4].markdown("**Analyze**")

for convo in displayed:
    cols = st.columns([2, 2, 2, 2, 2])
    cols[0].write(convo["username"])
    cols[1].write(convo["date_of_report"])
    cols[2].write(convo["conversation_id"])

    # View Button Logic
    if cols[3].button("View", key=f"view_{convo['conversation_id']}"):
        if st.session_state.open_view_id == convo["conversation_id"]:
            st.session_state.open_view_id = None  # Toggle off
        else:
            st.session_state.open_view_id = convo["conversation_id"]
            st.session_state.open_analyze_id = None

    # Analyze Button Logic
    if cols[4].button("Analyze", key=f"analyze_{convo['conversation_id']}"):
        if st.session_state.open_analyze_id == convo["conversation_id"]:
            st.session_state.open_analyze_id = None
        else:
            st.session_state.open_analyze_id = convo["conversation_id"]
            st.session_state.open_view_id = None

    # Render View Panel
    if st.session_state.open_view_id == convo["conversation_id"]:
        st.subheader(f"Past Analysis - {convo['conversation_id']}")
        if convo["results"]:
            for res in sorted(convo["results"], key=lambda r: r["time"], reverse=True):
                st.markdown(f"- **Time**: {res['time']}  \n"
                            f"- **Prompt ID**: <span style='color:#6cc644'>{res['prompt_id']}</span>  \n"
                            f"- **Model**: <span style='color:#4fa3d1'>{res['model']}</span><br>**Variables:**", unsafe_allow_html=True)
                for k, v in res["variables"].items():
                    if v == "":
                        st.markdown(f"""
                        <div style="margin-left: 20px;">
                            <strong style="color:#f0f0f0;">{k}:</strong> 
                            <span style="color:#ff4d4d;"><em>(missing)</em></span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="margin-left: 20px;">
                            <strong style="color:#f0f0f0;">{k}:</strong> 
                            <span style="color:#ccc;">{v}</span>
                        </div>
                        """, unsafe_allow_html=True)
                for m in res["output"]:
                    bubble_color = "#2a2d32" if m["role"] == "human" else "#1e4023"
                    st.markdown(f"<div style='background-color:{bubble_color}; padding:10px 15px; border-radius:10px; margin:8px 0; color:#f0f0f0;'><strong>{m['role'].capitalize()}:</strong><br>{m['content']}</div>", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No past analysis found.")

    # Render Analyze Panel
    if st.session_state.open_analyze_id == convo["conversation_id"]:
        st.subheader(f"New Analysis - {convo['conversation_id']}")
        prompt_list = fetch_prompt_list()
        selected_prompt = st.selectbox("Select Prompt", [""] + prompt_list, key=f"prompt_{convo['conversation_id']}")
        selected_model = st.selectbox("Select Model", ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"], key=f"model_{convo['conversation_id']}")
        
        variable_values = {}
        if selected_prompt.strip():
            input_variables = fetch_prompt_variables(selected_prompt)
            if input_variables:
                st.markdown("**Optional Variables:**")
                for var in input_variables:
                    value = st.text_input(f"{var} (optional)", key=f"{convo['conversation_id']}_{var}")
                    variable_values[var] = value if value.strip() else ""

        if st.button("Run Analysis", key=f"run_{convo['conversation_id']}"):
            try:
                json_payload = json.dumps(convo["content"])
                files = {"file": ("chat.json", json_payload, "application/json")}
                data = {
                    "prompt_id": selected_prompt,
                    "model_name": selected_model,
                    "variables_json": json.dumps(variable_values)
                }
                res = requests.post("http://localhost:8000/simulate", files=files, data=data)
                if res.status_code == 200:
                    output = res.json()
                    convo["results"].append({
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "prompt_id": selected_prompt,
                        "model": selected_model,
                        "variables": variable_values,
                        "output": output
                    })
                    save_single_conversation(convo)
                    st.success("Analysis completed.")
                    st.session_state.open_analyze_id = None
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Error during simulation: {e}")
