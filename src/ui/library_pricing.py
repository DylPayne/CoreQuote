import streamlit as st

from logic.database import get_active_price_list, get_price_list_items


def cents_to_amount(value: object) -> float:
    return float(int(value or 0) / 100.0)


def get_active_pricing_lookup() -> tuple[dict | None, dict[tuple[str, str], dict]]:
    active_price_list = get_active_price_list()
    if not active_price_list:
        return None, {}

    items = get_price_list_items(int(active_price_list["id"]))
    lookup = {(str(i["item_type"]), str(i["item_key"])): i for i in items}
    return active_price_list, lookup


def render_read_only_pricing_header(title: str) -> None:
    st.subheader(title)
    st.warning("Prices are managed in Pricing Admin. Update pricing there, not on this page.")
