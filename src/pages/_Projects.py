import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))

from logic.database import (
    get_all_projects, create_project, update_project, delete_project,
    get_quotes_for_project
)

st.title("📁 Projects")

# ── Dialogs ────────────────────────────────────────────────────────────────────

@st.dialog("➕ New Project", width="medium")
def new_project_dialog():
    with st.form("new_project_form", clear_on_submit=True):
        name = st.text_input("Project Name *", placeholder="e.g. Smith Kitchen")
        client = st.text_input("Client Name", placeholder="e.g. John Smith")
        address = st.text_input("Address", placeholder="e.g. 12 Oak Street, Cape Town")
        description = st.text_area("Description", placeholder="Optional notes…")
        if st.form_submit_button("Create Project", use_container_width=True):
            if name.strip():
                create_project(name.strip(), client.strip(), address.strip(), description.strip())
                st.success(f"Project '{name}' created!")
                st.rerun()
            else:
                st.error("Project name is required.")


@st.dialog("✏️ Edit Project", width="medium")
def edit_project_dialog(project: dict):
    with st.form("edit_project_form"):
        name = st.text_input("Project Name *", value=project["name"])
        client = st.text_input("Client Name", value=project["client"])
        address = st.text_input("Address", value=project.get("address", ""))
        description = st.text_area("Description", value=project["description"])
        col_save, col_del = st.columns(2)
        with col_save:
            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                if name.strip():
                    update_project(project["id"], name.strip(), client.strip(),
                                   address.strip(), description.strip())
                    st.success("Project updated!")
                    st.rerun()
                else:
                    st.error("Project name is required.")
        with col_del:
            if st.form_submit_button("🗑️ Delete Project", use_container_width=True,
                                     type="secondary"):
                delete_project(project["id"])
                if st.session_state.get("active_project_id") == project["id"]:
                    st.session_state.active_project_id = None
                st.rerun()


# ── Main layout ────────────────────────────────────────────────────────────────

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.subheader("All Projects")
with col_btn:
    if st.button("➕ New Project", use_container_width=True, type="primary"):
        new_project_dialog()

projects = get_all_projects()

if not projects:
    st.info("No projects yet. Click **➕ New Project** to get started.")
else:
    for p in projects:
        quotes = get_quotes_for_project(p["id"])
        quote_count = len(quotes)

        with st.container(border=True):
            col_info, col_open, col_edit = st.columns([5, 1, 1])
            with col_info:
                st.markdown(f"### {p['name']}")
                if p["client"]:
                    st.caption(f"👤 {p['client']}")
                if p.get("address"):
                    st.caption(f"📍 {p['address']}")
                if p["description"]:
                    st.caption(p["description"])
                st.caption(
                    f"🗂️ {quote_count} quote{'s' if quote_count != 1 else ''}  •  "
                    f"Created {p['created_at'][:10]}"
                )
            with col_open:
                if st.button("Open", key=f"open_{p['id']}", use_container_width=True,
                             type="primary"):
                    st.session_state.active_project_id = p["id"]
                    st.switch_page("pages/_Quotes.py")
            with col_edit:
                if st.button("Edit", key=f"edit_{p['id']}", use_container_width=True):
                    edit_project_dialog(p)
