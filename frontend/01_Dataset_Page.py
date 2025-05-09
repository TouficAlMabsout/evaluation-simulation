# frontend/01_Dataset_Page.py

import streamlit as st
from data_store import (
    load_dataset_names,
    create_dataset,
    delete_dataset,
    rename_dataset,
    load_conversations,
)
import math

# --- Config  ---------------------------------------------------
st.set_page_config(page_title="Dataset Selection", page_icon="📂")
st.title("📂 Datasets")

# --- Search  |  Refresh  |  Create  ----------------------------
hdr = st.columns([4, 1, 2])        # widths: search | refresh | create

def confirm_delete(name: str) -> None:
    delete_dataset(name)
    st.session_state.update({          # mark UI state
        "deleting_dataset": None,
        "dataset_convo_counts": {},    # force fresh counts next run
    })
    # toast instead of banner (avoids pushing content to the top)
    st.toast(f"Deleted '{name}' dataset", icon="🗑️")

with hdr[0]:
    search_query = st.text_input(
        "Search Datasets",
        placeholder="Type to search…",
        label_visibility="collapsed"
    )

with hdr[1]:
    def refresh_list() -> None:
        st.session_state.dataset_convo_counts.clear()   # drop cache
        # No st.rerun() here – Streamlit will rerun automatically.

    st.button("⟳", key="refresh_button", on_click=refresh_list)


with hdr[2]:
    st.button(
        "➕ Create Dataset",
        on_click=lambda: st.session_state.update(
            {"creating_dataset": not st.session_state.creating_dataset}
        )
    )

# --- Session State Initialization ---
for key, default in {
    "selected_dataset_name": None,
    "dataset_page": 1,
    "editing_dataset": None,
    "deleting_dataset": None,
    "creating_dataset": False,
    "dataset_convo_counts": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# --- Play any one-shot toast saved from the previous run -------------
if "pending_toast" in st.session_state:
    msg, icon = st.session_state.pending_toast
    st.toast(msg, icon=icon)
    del st.session_state.pending_toast


# --- Create Dataset Modal ---
if st.session_state.creating_dataset:
    st.markdown("---")
    new_name = st.text_input("New Dataset Name")
    create_cols = st.columns([2, 1, 2])
    with create_cols[0]:
        if st.button("✅ Create"):
            try:
                if new_name.strip() == "":
                    st.warning("Name cannot be empty.")
                elif new_name.strip() in load_dataset_names():
                    st.warning("A dataset with this name already exists.")
                else:
                    create_dataset(new_name.strip())
                    st.toast(f"Created dataset “{new_name.strip()}”", icon="📁")
                    st.session_state.creating_dataset = False
                    st.session_state.dataset_convo_counts.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"Error creating dataset: {e}")
    with create_cols[2]:
        st.button(
        "❌ Cancel",
        on_click=lambda: st.session_state.update({"creating_dataset": False})
        )

# --- Load Dataset Names & Filter ---
dataset_names = load_dataset_names()
if search_query:
    dataset_names = [d for d in dataset_names if search_query.lower() in d.lower()]

# --- Count conversations only when idle ---
if not st.session_state.creating_dataset and not st.session_state.editing_dataset and not st.session_state.deleting_dataset:
    for name in dataset_names:
        if name not in st.session_state.dataset_convo_counts:
            try:
                st.session_state.dataset_convo_counts[name] = len(load_conversations(name))
            except Exception:
                st.session_state.dataset_convo_counts[name] = 0

# --- Prepare Display Objects ---
dataset_objs = [{"name": name, "num_conversations": st.session_state.dataset_convo_counts.get(name, 0)} for name in dataset_names]
dataset_objs.sort(key=lambda d: d["name"].lower())

# --- Pagination Logic ---
datasets_per_page = 3
total_pages = max(1, math.ceil(len(dataset_objs) / datasets_per_page))
current_page = st.session_state.dataset_page
start = (current_page - 1) * datasets_per_page
end = start + datasets_per_page
visible_datasets = dataset_objs[start:end]
table_cols = [4, 2, 2, 2]
# --- Table Header ---
st.markdown("### ")
header_cols = st.columns(table_cols)
header_cols[0].markdown("**Name**")
header_cols[1].markdown("**Convos**")
header_cols[2].markdown("**Edit**")
header_cols[3].markdown("**Delete**")

# --- Dataset Rows ---
for ds in visible_datasets:
    is_selected = ds["name"] == st.session_state.selected_dataset_name
    row_cols = st.columns(table_cols)
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
                        st.session_state.pending_toast = (f"Renamed to “{new_name.strip()}”", "✏️")
                        st.session_state.editing_dataset = None
                        if ds["name"] == st.session_state.selected_dataset_name:
                            st.session_state.selected_dataset_name = new_name.strip()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error renaming: {e}")
            st.button(
                "❌ Cancel",
                key=f"cancel_rename_{ds['name']}",
                on_click=lambda: st.session_state.update({"editing_dataset": None})
            )

        else:
            st.button(ds["name"], key=f"select_{ds['name']}", on_click=lambda n=ds["name"]: st.session_state.update({"selected_dataset_name": n}), args=(), kwargs={})
            if row_style:
                st.markdown(f"<div style='{row_style}'></div>", unsafe_allow_html=True)

    with row_cols[1]:
        st.markdown(f"{ds['num_conversations']}")

    with row_cols[2]:
       st.button(
        "✏️",
        key=f"edit_{ds['name']}",
        on_click=lambda n=ds["name"]: st.session_state.update({
            "editing_dataset": None if st.session_state.editing_dataset == n else n
        }),
        args=(ds["name"],))

    # … your delete button …
    with row_cols[3]:
        # toggle open/close
        st.button(
            "🗑️",
            key=f"delete_{ds['name']}",
            on_click=lambda name=ds["name"]: st.session_state.update(
                {"deleting_dataset": None if st.session_state.deleting_dataset == name else name}
            )
        )

        # inline confirm (single-line message)
        if st.session_state.deleting_dataset == ds["name"]:
            st.markdown(
                f"""
                <style>
                .del-bubble {{
                    padding: 8px 14px;
                    border-radius: 8px;
                    margin: 6px 0 10px 0;
                    font-size: .92rem;
                    line-height: 1.35;
                    display: inline-block;
                    background-color: #f0f0f0; /* light-gray for fallback */
                    border: 1px solid #ccc;
                    color: #111;
                }}

                @media (prefers-color-scheme: dark) {{
                    .del-bubble {{
                        background-color: #1e1e1e;
                        border: 1px solid #444;
                        color: #f3f3f3;
                    }}
                }}
                </style>

                <div class="del-bubble">
                    Delete&nbsp;<strong>{ds['name']}</strong>?
                </div>
                """,
                unsafe_allow_html=True,
            )

            cnf, canc = st.columns(2)

            with cnf:
                st.button(
                    "✅",
                    key=f"confirm_delete_{ds['name']}",
                    on_click=confirm_delete,
                    args=(ds["name"],)
                )


            with canc:
                st.button(
                    "❌",
                    key=f"cancel_delete_{ds['name']}",
                    on_click=lambda: st.session_state.update({"deleting_dataset": None})
                )

# --- Pagination ---
st.divider()
pagination_cols = st.columns([2, 14, 2])
with pagination_cols[0]:
    if st.button("◀ Prev") and st.session_state.dataset_page > 1:
        st.session_state.dataset_page -= 1
        st.rerun()

with pagination_cols[2]:
    if st.button("Next ▶") and st.session_state.dataset_page < total_pages:
        st.session_state.dataset_page += 1
        st.rerun()

with pagination_cols[1]:
    st.markdown(
        f"<div style='text-align:center;'>Page {st.session_state.dataset_page} of {total_pages}</div>",
        unsafe_allow_html=True,
    )
