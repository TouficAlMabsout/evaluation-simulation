# ✅ Final optimized app.py (no more re-fetching on variable input)

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
if "prompt_vars_cache" not in st.session_state:
    st.session_state.prompt_vars_cache = {}
if "prompt_list" not in st.session_state:
    st.session_state.prompt_list = []

# API fetch functions
def fetch_prompt_list():
    try:
        res = requests.get("http://localhost:8000/prompts")
        return res.json() if res.status_code == 200 else []
    except:
        return []

def fetch_prompt_variables(prompt_id):
    try:
        res = requests.get("http://localhost:8000/prompt-variables", params={"prompt_id": prompt_id})
        return res.json().get("variables", []) if res.status_code == 200 else []
    except:
        return []

# Fetch prompts only once
if not st.session_state.prompt_list:
    st.session_state.prompt_list = fetch_prompt_list()

# UI Setup
st.title("Evaluation Dashboard")
conversations = st.session_state.conversations
with st.expander("Filter Options"):
    username_filter = st.text_input("Filter by Username")
    date_filter = st.date_input("Filter by Date", value=None, key="date_filter")

per_page = 3
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

filtered_conversations = [
    c for c in st.session_state.conversations
    if (username_filter.lower() in c["username"].lower()) and
       (not date_filter or c["date_of_report"].startswith(str(date_filter)))
]
total_pages = ceil(len(filtered_conversations) / per_page)
start = (st.session_state.current_page - 1) * per_page
end = start + per_page
displayed = filtered_conversations[start:end]

# Pagination
pagination_cols = st.columns([2, 14, 2])
with pagination_cols[0]:
    if st.button("\u25C0 Prev") and st.session_state.current_page > 1:
        st.session_state.current_page -= 1
with pagination_cols[2]:
    if st.button("Next \u25B6") and st.session_state.current_page < total_pages:
        st.session_state.current_page += 1
with pagination_cols[1]:
    st.markdown(f"<div style='text-align:center;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)

# ---------- Batch Simulation Panel ----------
if username_filter and filtered_conversations:
    st.markdown(f"**Simulate all chats for user:** `{username_filter}`")

    selected_prompt = st.selectbox("Select Prompt", [""] + st.session_state.prompt_list, key="batch_prompt")
    selected_model = st.selectbox("Select Model", ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"], key="batch_model")

    if selected_prompt and selected_prompt not in st.session_state.prompt_vars_cache:
        st.session_state.prompt_vars_cache[selected_prompt] = fetch_prompt_variables(selected_prompt)

    variable_values = {}
    prompt_vars = st.session_state.prompt_vars_cache.get(selected_prompt, [])
    for var in prompt_vars:
        val = st.text_input(f"{var} (optional)", key=f"batch_input_{var}")
        variable_values[var] = val if val.strip() else ""

    if st.button("Simulate All Chats for This User"):
        if not selected_prompt:
            st.error("Please select a prompt before simulating.")
        else:
            for convo in filtered_conversations:
                json_payload = json.dumps(convo["content"])
                files = {"file": ("chat.json", json_payload, "application/json")}
                data = {
                    "prompt_id": selected_prompt,
                    "model_name": selected_model,
                    "variables_json": json.dumps(variable_values)
                }
                try:
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
                    else:
                        st.warning(f"Error simulating chat {convo['conversation_id']}: {res.status_code}")
                except Exception as e:
                    st.warning(f"Simulation failed for chat {convo['conversation_id']}: {e}")
            st.success("All chats simulated successfully.")

# ---------- Header Row ----------
st.divider()
header_cols = st.columns([3, 7, 6, 3, 4, 4])
header_cols[0].markdown("**User**")
header_cols[1].markdown("**Submitted At**")
header_cols[2].markdown("**Chat ID**")
header_cols[3].markdown("**Sim Count**")
header_cols[4].markdown("**History**")
header_cols[5].markdown("**Simulate**")

# ---------- Individual Chat Rows ----------
for convo in displayed:
    cols = st.columns([3, 7, 6, 3, 4, 4])
    cols[0].write(convo["username"])
    try:
        dt_obj = datetime.fromisoformat(convo["date_of_report"].replace("Z", "+00:00"))
        formatted_time = dt_obj.strftime("%b %d, %Y - %I:%M %p")
    except:
        formatted_time = convo["date_of_report"]
    cols[1].write(formatted_time)
    cols[2].write(convo["conversation_id"])
    cols[3].write(str(len(convo.get("results", []))))

    if cols[4].button("View", key=f"view_{convo['conversation_id']}"):
        st.session_state.open_view_id = None if st.session_state.open_view_id == convo["conversation_id"] else convo["conversation_id"]
        st.session_state.open_analyze_id = None

    if cols[5].button("Simulate", key=f"analyze_{convo['conversation_id']}"):
        st.session_state.open_analyze_id = None if st.session_state.open_analyze_id == convo["conversation_id"] else convo["conversation_id"]
        st.session_state.open_view_id = None

    if st.session_state.open_view_id == convo["conversation_id"]:
        st.subheader(f"Past Simulations - {convo['conversation_id']}")
        if convo["results"]:
            for res in sorted(convo["results"], key=lambda r: r["time"], reverse=True):
                try:
                    dt_obj = datetime.fromisoformat(res["time"])
                    formatted_time = dt_obj.strftime("%b %d, %Y - %I:%M %p")
                except:
                    formatted_time = res["time"]
                st.markdown(f"- **Time**: {formatted_time}  \n**Prompt ID**: <span style='color:#6cc644'>{res['prompt_id']}</span>  \n**Model**: <span style='color:#4fa3d1'>{res['model']}</span><br>**Variables:**", unsafe_allow_html=True)
                for k, v in res["variables"].items():
                    color = "#ff4d4d" if v == "" else "#ccc"
                    value = "<em>(missing)</em>" if v == "" else v
                    st.markdown(f"<div style='margin-left: 20px;'><strong style='color:#f0f0f0;'>{k}:</strong> <span style='color:{color};'>{value}</span></div>", unsafe_allow_html=True)
                for m in res["output"]:
                    bubble_color = "#2a2d32" if m["role"] == "human" else "#1e4023"
                    st.markdown(f"<div style='background-color:{bubble_color}; padding:10px 15px; border-radius:10px; margin:8px 0; color:#f0f0f0;'><strong>{m['role'].capitalize()}:</strong><br>{m['content']}</div>", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No past simulation found.")

    if st.session_state.open_analyze_id == convo["conversation_id"]:
        st.subheader(f"New Simulation - {convo['conversation_id']}")

        selected_prompt = st.selectbox("Select Prompt", [""] + st.session_state.prompt_list, key=f"prompt_{convo['conversation_id']}")
        selected_model = st.selectbox("Select Model", ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"], key=f"model_{convo['conversation_id']}")

        if selected_prompt and selected_prompt not in st.session_state.prompt_vars_cache:
            st.session_state.prompt_vars_cache[selected_prompt] = fetch_prompt_variables(selected_prompt)

        variable_values = {}
        prompt_vars = st.session_state.prompt_vars_cache.get(selected_prompt, [])
        for var in prompt_vars:
            val = st.text_input(f"{var} (optional)", key=f"{convo['conversation_id']}_{var}")
            variable_values[var] = val if val.strip() else ""

        if st.button("Simulate", key=f"run_{convo['conversation_id']}"):
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
                    st.success("Simulation completed.")
                    st.session_state.open_analyze_id = None
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Error during simulation: {e}")
