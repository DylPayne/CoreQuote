from __future__ import annotations

from collections.abc import Callable

import streamlit as st


def render_inventory_pricing_tabs(
    *,
    render_inventory: Callable[[], None],
    render_pricing: Callable[[], None],
    inventory_label: str = "Current Inventory",
    pricing_label: str = "Pricing",
) -> None:
    tab_inventory, tab_pricing = st.tabs([inventory_label, pricing_label])

    with tab_inventory:
        render_inventory()

    with tab_pricing:
        render_pricing()
