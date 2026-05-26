from __future__ import annotations

import streamlit as st


def render_page_header(title: str, back_label: str | None = None, back_target: str | None = None) -> None:
    if back_label and back_target:
        col_back, col_title = st.columns([1, 6])
        with col_back:
            if st.button(back_label):
                st.switch_page(back_target)
        with col_title:
            st.title(title)
        return

    st.title(title)


def render_empty_state(message: str) -> None:
    st.info(message)
