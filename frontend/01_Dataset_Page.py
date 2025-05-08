# frontend/01_Dataset_Page.py

import streamlit as st
from data_store import (
    load_dataset_names,
    create_dataset,
    delete_dataset,
    rename_dataset,
    load_conversations
)
import math

# --- Config ---
st.set_page_config(page_title="Dataset Selection", page_icon="📂")
st.title("📂 Datasets")

# --- Session State ---
if "selected_dataset_name" not in st.session_state:
    st.session_state.selected_dataset_name = None
if "dataset_page" not in st.session_state:
    st.session_state.dataset_page = 1
if "editing_dataset" not in st.session_state:
    st.session_state.editing_dataset = None
if "deleting_dataset" not in st.session_state:
    st.session_state.deleting_dataset = None
if "creating_dataset" not in st.session_state:
    st.session_state.creating_dataset = False

# --- Header: Search + Create ---
cols = st.columns([4, 2])
with cols[0]:
    search_query = st.text_input("Search Datasets", placeholder="Type to search...", label_visibility="collapsed")
with cols[1]:
    if st.button("+ Create Dataset"):
        st.session_state.creating_dataset = True

# --- Create Dataset Modal ---
if st.session_state.creating_dataset:
    with st.container():
        st.markdown("---")
        new_name = st.text_input("New Dataset Name")
        create_cols = st.columns([1, 1])
        with create_cols[0]:
            if st.button("✅ Create"):
                try:
                    if new_name.strip() == "":
                        st.warning("Name cannot be empty.")
                    elif new_name.strip() in load_dataset_names():
                        st.warning("A dataset with this name already exists.")
                    else:
                        create_dataset(new_name.strip())
                        st.success(f"Dataset '{new_name.strip()}' created.")
                        st.session_state.creating_dataset = False
                        st.rerun()
                except Exception as e:
                    st.error(f"Error creating dataset: {e}")
        with create_cols[1]:
            if st.button("❌ Cancel"):
                st.session_state.creating_dataset = False

# --- Load & Filter ---
dataset_names = load_dataset_names()
dataset_objs = [{"name": name, "num_conversations": len(load_conversations(name))} for name in dataset_names]

if search_query:
    dataset_objs = [d for d in dataset_objs if search_query.lower() in d["name"].lower()]

# --- Pagination ---
datasets_per_page = 10
total_pages = max(1, math.ceil(len(dataset_objs) / datasets_per_page))
current_page = st.session_state.dataset_page
start = (current_page - 1) * datasets_per_page
end = start + datasets_per_page
visible_datasets = dataset_objs[start:end]

# --- Table Header ---
st.markdown("### ")
header_cols = st.columns([6, 2, 1, 1])
header_cols[0].markdown("**Name**")
header_cols[1].markdown("**Convos**")
header_cols[2].markdown("**Edit**")
header_cols[3].markdown("**Delete**")

# --- Rows ---
for ds in visible_datasets:
    is_selected = ds["name"] == st.session_state.selected_dataset_name
    row_cols = st.columns([6, 2, 1, 1])
    row_style = "background-color: rgba(0, 123, 255, 0.15); border-radius: 5px; padding: 4px;" if is_selected else ""

    with row_cols[0]:
        if st.session_state.editing_dataset == ds["name"]:
            new_name = st.text_input("Rename to:", value=ds["name"], key=f"rename_input_{ds['name']}")
            if st.button("💾 Save", key=f"save_rename_{ds['name']}"):
                try:
                    if new_name.strip() == "":
                        st.warning("New name cannot be empty.")
                    elif new_name.strip() in load_dataset_names():
                        st.warning("That name already exists.")
                    else:
                        rename_dataset(ds["name"], new_name.strip())
                        st.session_state.editing_dataset = None
                        if ds["name"] == st.session_state.selected_dataset_name:
                            st.session_state.selected_dataset_name = new_name.strip()
                        st.success("Renamed successfully.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error renaming: {e}")
            if st.button("❌ Cancel", key=f"cancel_rename_{ds['name']}"):
                st.session_state.editing_dataset = None
        else:
            if st.button(ds["name"], key=f"select_{ds['name']}"):
                st.session_state.selected_dataset_name = ds["name"]
                st.switch_page("pages/02_Chat_Page.py")
            if row_style:
                st.markdown(f"<div style='{row_style}'></div>", unsafe_allow_html=True)

    with row_cols[1]:
        st.markdown(f"{ds['num_conversations']}")

    with row_cols[2]:
        if st.button("✏️", key=f"edit_{ds['name']}"):
            st.session_state.editing_dataset = ds["name"]

    with row_cols[3]:
        if st.button("🗑️", key=f"delete_{ds['name']}"):
            st.session_state.deleting_dataset = ds["name"]

# --- Delete Confirmation Modal ---
if st.session_state.deleting_dataset:
    st.markdown("---")
    st.warning(f"Are you sure you want to delete **{st.session_state.deleting_dataset}**?")
    confirm_cols = st.columns([1, 1])
    with confirm_cols[0]:
        if st.button("✅ Yes, Delete"):
            try:
                delete_dataset(st.session_state.deleting_dataset)
                st.success("Dataset deleted.")
                if st.session_state.selected_dataset_name == st.session_state.deleting_dataset:
                    st.session_state.selected_dataset_name = None
                st.session_state.deleting_dataset = None
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting: {e}")
    with confirm_cols[1]:
        if st.button("❌ Cancel Delete"):
            st.session_state.deleting_dataset = None

# --- Pagination Controls ---
if total_pages > 1:
    pag_cols = st.columns(total_pages)
    for i in range(total_pages):
        if pag_cols[i].button(str(i + 1), key=f"pg_{i+1}"):
            st.session_state.dataset_page = i + 1
