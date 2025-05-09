# pages/02_Chat_Page.py

import streamlit as st
import requests
from dotenv import load_dotenv
import json
from datetime import datetime
from math import ceil
import sys, os
import pytz
import time

# Fix import path for shared modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data_store import load_conversations, save_single_conversation, load_dataset_names, delete_conversation, duplicate_conversation

# Load environment variables (from root)
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL")

# Set tab title
st.set_page_config(
    page_title="Evaluation Simulation",
    page_icon="🤖"
)

# JavaScript timezone detection
from streamlit_javascript import st_javascript
timezone = st_javascript("""await (async () => {
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return userTimezone
})().then(returnValue => returnValue)""")

# Set timezone in session
if "user_timezone" not in st.session_state:
    st.session_state.user_timezone = timezone or "Asia/Dubai"
user_tz_str = st.session_state.get("user_timezone", "Asia/Dubai")
try:
    user_tz = pytz.timezone(user_tz_str)
except pytz.UnknownTimeZoneError:
    user_tz = pytz.timezone("Asia/Dubai")

# ✅ Force sync of selected dataset (and reset old conversations + filters if dataset changed)
selected = st.session_state.get("selected_dataset_name")
prev = st.session_state.get("dataset_name")

if selected and selected != prev:
    st.session_state.dataset_name = selected
    st.session_state.conversations = load_conversations(selected)
    st.session_state.current_page = 1
    st.session_state.start_date = None
    st.session_state.end_date = None
    st.session_state.user_filter = ""
    st.session_state.chat_id_filter = ""

# ⚠️ Fallback if no dataset selected
if "dataset_name" not in st.session_state or not st.session_state.dataset_name:
    st.error("No dataset selected. Please go back and select a dataset.")
    st.stop()

# Load conversations once
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

# LLM options
MODEL_OPTIONS = {
    "claude": [
        "claude-3-haiku-20240307",
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229"
    ],
    "openai": [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo"
    ],
    "gemini": [
        "models/gemini-1.5-pro-latest", 
        "models/gemini-1.5-flash-latest"
    ]
}

def fetch_prompt_list():
    try:
        res = requests.get(f"{BACKEND_URL}/prompts", params={"workspace": st.session_state.workspace})
        if res.status_code == 200:
            return res.json()
        return []
    except:
        return []

def fetch_prompt_variables(prompt_id):
    try:
        res = requests.get(f"{BACKEND_URL}/prompt-variables", params={
            "prompt_id": prompt_id,
            "workspace": st.session_state.workspace
        })
        if res.status_code == 200:
            return res.json().get("variables", [])
        return []
    except:
        return []

# Filtering helpers
def is_within_range(convo_date):
    try:
        convo_dt = datetime.fromisoformat(convo_date.replace("Z", "+00:00")).date()
        if start_date and convo_dt < start_date:
            return False
        if end_date and convo_dt > end_date:
            return False
        return True
    except:
        return False

def matches_filters(convo):
    if not is_within_range(convo["date_of_report"]): return False
    if user_filter.strip() and user_filter.lower() not in convo.get("username", "").lower(): return False
    if chat_id_filter.strip() and chat_id_filter.lower() not in convo.get("conversation_id", "").lower(): return False
    return True

# Title and back navigation
st.title("Evaluation Dashboard")
if st.button("← Back to Datasets"):
    st.session_state.open_analyze_id = None
    st.session_state.open_view_id = None
    st.session_state.open_details_id = None
    st.session_state.current_page = 1
    st.session_state.start_date = None
    st.session_state.end_date = None
    st.session_state.user_filter = ""
    st.session_state.chat_id_filter = ""
    st.switch_page("01_Dataset_Page.py")


# Workspace selection
workspace_options = ["MaidsAT-Delighters-Doctors", "Resolvers", "Sales"]
if "workspace" not in st.session_state:
    st.session_state.workspace = workspace_options[0]

st.session_state.workspace = st.selectbox("Select Workspace", workspace_options)

# ✅ Prompt list fetch
if not st.session_state.prompt_list:
    st.session_state.prompt_list = fetch_prompt_list()

if st.button("⟳ Refresh Conversations"):
    st.session_state.conversations = load_conversations(st.session_state.dataset_name)
    st.success(f"Refreshed dataset: {st.session_state.dataset_name}")


conversations = st.session_state.conversations
with st.expander("Filter Options"):
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date (optional)", value=None, key="start_date")
        # 🔹 NEW
        user_filter = st.text_input("User (optional)", value="", key="user_filter")
    with col2:
        end_date   = st.date_input("End Date (optional)", value=None, key="end_date")
        # 🔹 NEW
        chat_id_filter = st.text_input("Chat ID (optional)", value="", key="chat_id_filter")

    if start_date and end_date and start_date > end_date:
        st.error("Start date cannot be after end date.")
    
    # ── NEW: reset to page 1 whenever any filter is active ──
    if st.session_state.get("current_page", 1) != 1 and (
        start_date or end_date or user_filter or chat_id_filter
    ):
        st.session_state.current_page = 1 

per_page = 10
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

filtered_conversations = [c for c in st.session_state.conversations if matches_filters(c)]

total_pages = max(1,ceil(len(filtered_conversations) / per_page))
start = (st.session_state.current_page - 1) * per_page
end = start + per_page
displayed = filtered_conversations[start:end]
if not displayed:
    st.warning("No conversations found with the current filters.")

st.markdown(f"### Simulate All – **{st.session_state.dataset_name}**")
selected_prompt = st.selectbox("Select Prompt", [""] + st.session_state.prompt_list, key="dataset_prompt")
selected_family = st.selectbox("Select Model Family", list(MODEL_OPTIONS.keys()), key="model_family")
selected_submodel = st.selectbox("Select Submodel", MODEL_OPTIONS[selected_family], key="submodel")
selected_model = f"{selected_family}:{selected_submodel}"

if selected_prompt and selected_prompt not in st.session_state.prompt_vars_cache:
    st.session_state.prompt_vars_cache[selected_prompt] = fetch_prompt_variables(selected_prompt)

dataset_variable_values = {}
prompt_vars = st.session_state.prompt_vars_cache.get(selected_prompt, [])
for var in prompt_vars:
    val = st.text_input(f"{var} (optional)", key=f"dataset_input_{var}")
    dataset_variable_values[var] = val if val.strip() else ""

if st.button("Simulate All"):
    if not selected_prompt:
        st.warning("Please select a prompt before running simulation.")
    else:
        failed = []
        for convo in filtered_conversations:
            json_payload = json.dumps(convo["content"])
            files = {"file": ("chat.json", json_payload, "application/json")}
            data = {
                "prompt_id": selected_prompt,
                "model_name": selected_model,
                "variables_json": json.dumps(dataset_variable_values),
                "workspace": st.session_state.workspace
            }
            try:
                res = requests.post(f"{BACKEND_URL}/simulate", files=files, data=data)
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
                    failed.append((convo["conversation_id"], res.status_code, res.text))
                    st.error(f"❌ Error simulating chat {convo['conversation_id']}: {res.status_code} - {res.text}")
            except Exception as e:
                failed.append((convo["conversation_id"], "Exception", str(e)))
                st.error(f"❌ Exception simulating chat {convo['conversation_id']}: {e}")
        if failed:
            st.warning(f"{len(failed)} conversation(s) failed.")
        else:
            st.success("All conversations simulated successfully.")
        
        # 🔄 trigger table refresh so every Sim Count updates right away
        st.session_state["sim_refresh_all"] = time.time()
        st.rerun()

# ---------- Header Row ----------
col_sizes = [2, 3, 5, 5, 2, 3, 3] 
st.divider()
header_cols = st.columns(col_sizes)
header_cols[1].markdown("**User**")
header_cols[2].markdown("**Submitted At**")
header_cols[3].markdown("**Chat ID**")
header_cols[4].markdown("**Sim Count**")
header_cols[5].markdown("**History**")
header_cols[6].markdown("**Simulate**")

# ---------- Individual Chat Rows ----------
for convo in displayed:
    cols = st.columns(col_sizes)
    cols[1].write(convo["username"])
    try:
        dt_obj = datetime.fromisoformat(convo["date_of_report"].replace("Z", "+00:00"))
        local_time = dt_obj.astimezone(user_tz)
        formatted_time = local_time.strftime("%b %d, %Y - %I:%M %p")
    except:
        formatted_time = convo["date_of_report"]
    cols[2].write(formatted_time)
    cols[3].write(convo["conversation_id"])
    cols[4].write(str(len(convo.get("results", []))))


    if cols[5].button("View", key=f"view_{convo['conversation_id']}"):
        st.session_state.open_view_id = None if st.session_state.open_view_id == convo["conversation_id"] else convo["conversation_id"]
        st.session_state.open_analyze_id = None
        st.session_state.open_details_id = None

    if cols[6].button("Start", key=f"analyze_{convo['conversation_id']}"):
        st.session_state.open_analyze_id = None if st.session_state.open_analyze_id == convo["conversation_id"] else convo["conversation_id"]
        st.session_state.open_view_id = None
        st.session_state.open_details_id = None

    if cols[0].button("ⓘ", key=f"details_{convo['conversation_id']}"):
        st.session_state.open_details_id = (
            None if st.session_state.get("open_details_id") == convo["conversation_id"]
            else convo["conversation_id"]
        )
        st.session_state.open_view_id = None
        st.session_state.open_analyze_id = None


    if st.session_state.open_view_id == convo["conversation_id"]:
        st.subheader(f"Past Simulations - {convo['conversation_id']}")
        if convo["results"]:
            for res in sorted(convo["results"], key=lambda r: r["time"], reverse=True):
                try:
                    dt_obj = datetime.fromisoformat(res["time"])
                    local_time = dt_obj.astimezone(user_tz)
                    formatted_time = local_time.strftime("%b %d, %Y - %I:%M %p")
                except:
                    formatted_time = res["time"]
                st.markdown(f"- **Time**: {formatted_time}  \n**Prompt ID**: <span style='color:#6cc644'>{res['prompt_id']}</span>  \n**Model**: <span style='color:#4fa3d1'>{res['model']}</span><br>**Variables:**", unsafe_allow_html=True)
                # variables display
                if res["variables"]:
                    for k, v in res["variables"].items():
                        style = "opacity:0.5;" if v != "" else "color:#ff4d4d;"
                        value = "<em>(missing)</em>" if v == "" else v
                        st.markdown(
                            f"<div style='margin-left: 20px;'><strong style='opacity:0.85;'>{k}:</strong> <span style='{style}'>{value}</span></div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        "<div style='margin-left:20px; opacity:0.5;'><em>No variables for this prompt.</em></div>",
                        unsafe_allow_html=True,
                    )
                for m in res["output"]:
                    bubble_color = "#2a2d32" if m["role"] == "human" else "#1e4023"
                    st.markdown(f"<div style='background-color:{bubble_color}; padding:10px 15px; border-radius:10px; margin:8px 0; color:#f0f0f0;'><strong>{m['role'].capitalize()}:</strong><br>{m['content']}</div>", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No past simulation found.")

    if st.session_state.open_analyze_id == convo["conversation_id"]:
        st.subheader(f"New Simulation - {convo['conversation_id']}")

        selected_prompt = st.selectbox("Select Prompt", [""] + st.session_state.prompt_list, key=f"prompt_{convo['conversation_id']}")
        family_key = f"{convo['conversation_id']}_model_family"
        submodel_key = f"{convo['conversation_id']}_submodel"

        selected_family = st.selectbox("Select Model Family", list(MODEL_OPTIONS.keys()), key=family_key)
        selected_submodel = st.selectbox("Select Submodel", MODEL_OPTIONS[selected_family], key=submodel_key)
        selected_model = f"{selected_family}:{selected_submodel}"

        if selected_prompt and selected_prompt not in st.session_state.prompt_vars_cache:
            st.session_state.prompt_vars_cache[selected_prompt] = fetch_prompt_variables(selected_prompt)

        variable_values = {}
        prompt_vars = st.session_state.prompt_vars_cache.get(selected_prompt, [])
        for var in prompt_vars:
            val = st.text_input(f"{var} (optional)", key=f"{convo['conversation_id']}_{var}")
            variable_values[var] = val if val.strip() else ""

        if st.button("Run", key=f"run_{convo['conversation_id']}"):
            if not selected_prompt:
                st.warning("Please select a prompt before running simulation.")
            else:
                try:
                    json_payload = json.dumps(convo["content"])
                    files = {"file": ("chat.json", json_payload, "application/json")}
                    data = {
                        "prompt_id": selected_prompt,
                        "model_name": selected_model,
                        "variables_json": json.dumps(variable_values),
                        "workspace": st.session_state.workspace
                    }

                    res = requests.post(f"{BACKEND_URL}/simulate", files=files, data=data)

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
                        # 🔄 Trigger table refresh so Sim Count updates immediately
                        st.session_state[f"sim_refresh_{convo['conversation_id']}"] = time.time()
                        st.success("Simulation completed.")
                        st.session_state.open_analyze_id = None
                        st.rerun() 
                    else:
                        st.error(f"❌ Error simulating chat {convo['conversation_id']}: {res.status_code} - {res.text}")

                except Exception as e:
                    st.error(f"❌ Exception during simulation of chat {convo['conversation_id']}: {e}")
                    
    if st.session_state.get("open_details_id") == convo["conversation_id"]:
        st.markdown(f"#### Chat Details - {convo['conversation_id']}")

        for msg in convo["content"]:
            if msg["role"] == "human":
                st.markdown(
                    f"<div style='background-color:#2a2d32; padding:10px 15px; border-radius:10px; margin:8px 0; color:#f0f0f0;'><strong>Human:</strong><br>{msg['content']}</div>",
                    unsafe_allow_html=True,
                )

        if st.button("🗑️ Delete this Chat", key=f"delete_{convo['conversation_id']}"):
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
st.divider()
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





