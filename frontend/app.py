# ✅ Final optimized app.py (no more re-fetching on variable input)

import streamlit as st
import requests
from dotenv import load_dotenv
import json
from datetime import datetime
from math import ceil
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data_store import load_conversations, save_single_conversation, load_dataset_names, create_dataset, delete_dataset, delete_conversation, duplicate_conversation

# Load environment variables
load_dotenv()

# Init session state
if "dataset_name" not in st.session_state:
    dataset_names = load_dataset_names()
    st.session_state.dataset_name = dataset_names[0] if dataset_names else ""
if "conversations" not in st.session_state:
    st.session_state.conversations = load_conversations(st.session_state.dataset_name)
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

with st.expander("▦ Dataset Management"):
    new_name = st.text_input("Create New Dataset", placeholder="Enter dataset name")
    if st.button("✚ Create Dataset"):
        try:
            if new_name.strip() in load_dataset_names():
                st.warning("A dataset with that name already exists.")
            else:
                create_dataset(new_name.strip())
                st.success(f"Dataset '{new_name.strip()}' created successfully.")
                st.rerun()
        except Exception as e:
            st.error(f"Failed to create dataset: {e}")

    selected_for_deletion = st.selectbox("Delete Existing Dataset", load_dataset_names())
    if st.button("🗑 Delete Selected Dataset"):
        try:
            delete_dataset(selected_for_deletion)
            st.success(f"Dataset '{selected_for_deletion}' deleted.")
            if selected_for_deletion == st.session_state.dataset_name:
                st.session_state.dataset_name = ""
            st.rerun()
        except Exception as e:
            st.error(f"Failed to delete dataset: {e}")

# Dataset selector
dataset_names = load_dataset_names()
if "dataset_name" not in st.session_state:
    st.session_state.dataset_name = dataset_names[0] if dataset_names else ""

selected_dataset = st.selectbox("Select Dataset", dataset_names, index=dataset_names.index(st.session_state.dataset_name) if st.session_state.dataset_name in dataset_names else 0)
if selected_dataset != st.session_state.dataset_name:
    st.session_state.dataset_name = selected_dataset
    st.session_state.conversations = load_conversations(selected_dataset)
    st.rerun()


if st.button("⟳ Refresh Conversations"):
    st.session_state.conversations = load_conversations(st.session_state.dataset_name)
    st.success(f"Refreshed dataset: {st.session_state.dataset_name}")


conversations = st.session_state.conversations
with st.expander("Filter Options"):
    date_filter = st.date_input("Filter by Date", value=None, key="date_filter")

per_page = 3
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

filtered_conversations = [
    c for c in st.session_state.conversations
    if not date_filter or c["date_of_report"].startswith(str(date_filter))
]

total_pages = max(1,ceil(len(filtered_conversations) / per_page))
start = (st.session_state.current_page - 1) * per_page
end = start + per_page
displayed = filtered_conversations[start:end]
if not displayed:
    st.warning("No conversations found with the current filters.")

# Pagination
pagination_cols = st.columns([2, 14, 2])
with pagination_cols[0]:
    if st.button("\u25C0 Prev") and st.session_state.current_page > 1:
        st.session_state.current_page -= 1
        st.rerun()
        
with pagination_cols[2]:
    if st.button("Next \u25B6") and st.session_state.current_page < total_pages:
        st.session_state.current_page += 1
        st.rerun()

with pagination_cols[1]:
    st.markdown(f"<div style='text-align:center;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)

st.markdown("### Simulate All Conversations in This Dataset")

selected_prompt = st.selectbox("Select Prompt", [""] + st.session_state.prompt_list, key="dataset_prompt")
selected_model = st.selectbox("Select Model", ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"], key="dataset_model")

if selected_prompt and selected_prompt not in st.session_state.prompt_vars_cache:
    st.session_state.prompt_vars_cache[selected_prompt] = fetch_prompt_variables(selected_prompt)

dataset_variable_values = {}
prompt_vars = st.session_state.prompt_vars_cache.get(selected_prompt, [])
for var in prompt_vars:
    val = st.text_input(f"{var} (optional)", key=f"dataset_input_{var}")
    dataset_variable_values[var] = val if val.strip() else ""

if st.button("Simulate All"):
    for convo in filtered_conversations:
        json_payload = json.dumps(convo["content"])
        files = {"file": ("chat.json", json_payload, "application/json")}
        data = {
            "prompt_id": selected_prompt,
            "model_name": selected_model,
            "variables_json": json.dumps(dataset_variable_values)
        }
        try:
            res = requests.post("http://localhost:8000/simulate", files=files, data=data)
            if res.status_code == 200:
                output = res.json()
                convo["results"].append({
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "prompt_id": selected_prompt,
                    "model": selected_model,
                    "variables": dataset_variable_values,
                    "output": output
                })
                save_single_conversation(convo, st.session_state.dataset_name)
            else:
                st.warning(f"Error simulating chat {convo['conversation_id']}: {res.status_code}")
        except Exception as e:
            st.warning(f"Simulation failed for chat {convo['conversation_id']}: {e}")
    st.success("All conversations simulated successfully.")

# ---------- Header Row ----------
st.divider()
header_cols = st.columns([2, 3, 7, 7, 3, 4, 5])
header_cols[1].markdown("**User**")
header_cols[2].markdown("**Submitted At**")
header_cols[3].markdown("**Chat ID**")
header_cols[4].markdown("**Sim Count**")
header_cols[5].markdown("**History**")
header_cols[6].markdown("**Simulate**")

# ---------- Individual Chat Rows ----------
for convo in displayed:
    cols = st.columns([2, 3, 7, 7, 3, 4, 5])
    cols[1].write(convo["username"])
    try:
        dt_obj = datetime.fromisoformat(convo["date_of_report"].replace("Z", "+00:00"))
        formatted_time = dt_obj.strftime("%b %d, %Y - %I:%M %p")
    except:
        formatted_time = convo["date_of_report"]
    cols[2].write(formatted_time)
    cols[3].write(convo["conversation_id"])
    cols[4].write(str(len(convo.get("results", []))))

    if cols[5].button("View", key=f"view_{convo['conversation_id']}"):
        st.session_state.open_view_id = None if st.session_state.open_view_id == convo["conversation_id"] else convo["conversation_id"]
        st.session_state.open_analyze_id = None

    if cols[6].button("Simulate", key=f"analyze_{convo['conversation_id']}"):
        st.session_state.open_analyze_id = None if st.session_state.open_analyze_id == convo["conversation_id"] else convo["conversation_id"]
        st.session_state.open_view_id = None

    if cols[0].button("🛈", key=f"details_{convo['conversation_id']}"):
        st.session_state.open_details_id = (
            None if st.session_state.get("open_details_id") == convo["conversation_id"]
            else convo["conversation_id"]
        )


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
                    save_single_conversation(convo, st.session_state.dataset_name)
                    st.success("Simulation completed.")
                    st.session_state.open_analyze_id = None
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Error during simulation: {e}")
    
    if st.session_state.get("open_details_id") == convo["conversation_id"]:
        st.markdown(f"#### Chat Details – {convo['conversation_id']}")

        for msg in convo["content"]:
            if msg["role"] == "human":
                st.markdown(
                    f"<div style='background-color:#2a2d32; padding:10px 15px; border-radius:10px; margin:8px 0; color:#f0f0f0;'><strong>Human:</strong><br>{msg['content']}</div>",
                    unsafe_allow_html=True,
                )

        if st.button("🗑 Delete this Chat", key=f"delete_{convo['conversation_id']}"):
            delete_conversation(st.session_state.dataset_name, convo["conversation_id"])
            st.success(f"Chat {convo['conversation_id']} deleted.")
            st.session_state.conversations = load_conversations(st.session_state.dataset_name)
            st.rerun()
        with st.expander("⧉ Duplicate this Chat"):
            target_dataset = st.selectbox(
                "Select destination dataset",
                [d for d in load_dataset_names() if d != st.session_state.dataset_name],
                key=f"copy_target_{convo['conversation_id']}"
            )

            col_copy1, col_copy2 = st.columns(2)

            with col_copy1:
                if st.button("⎘ Copy With Results", key=f"copy_with_{convo['conversation_id']}"):
                    duplicate_conversation(convo, target_dataset, clear_results=False)
                    st.success(f"Chat copied to '{target_dataset}' with results")

            with col_copy2:
                if st.button("⎚ Copy Without Results", key=f"copy_empty_{convo['conversation_id']}"):
                    duplicate_conversation(convo, target_dataset, clear_results=True)
                    st.success(f"Chat copied to '{target_dataset}' without results")




