from __future__ import annotations


def board_index_for_id(board_ids: list[int | None], board_id: int | None) -> int:
    if board_id in board_ids:
        return board_ids.index(board_id)
    return 0


def slide_payload_from_id(slide_lookup: dict[int, dict], slide_id: int | None) -> dict:
    if slide_id is None:
        return {}
    row = slide_lookup.get(slide_id)
    if not row:
        return {}
    return {
        "brand": str(row["brand"]),
        "model": str(row["model"]),
        "code": str(row["code"]),
        "length": int(row["length"]),
        "side_length": int(row["side_length"]),
        "side_clearance_total": int(row["side_clearance_total"]),
        "side_height_uplift": int(row.get("side_height_uplift", 0) or 0),
    }


def hinge_payload_from_id(hinge_lookup: dict[int, dict], hinge_id: int | None) -> dict:
    if hinge_id is None:
        return {}
    row = hinge_lookup.get(hinge_id)
    if not row:
        return {}
    return {
        "brand": str(row["brand"]),
        "model": str(row["model"]),
        "code": str(row["code"]),
        "opening_angle_deg": int(row["opening_angle_deg"]),
    }


def handle_payload_from_id(handle_lookup: dict[int, dict], handle_id: int | None) -> dict:
    if handle_id is None:
        return {}
    row = handle_lookup.get(handle_id)
    if not row:
        return {}
    return {
        "name": str(row["name"]),
        "supplier": str(row["supplier"]),
        "code": str(row["code"]),
    }


def slide_id_from_quote(slides: list[dict], slide_ids: list[int], quote: dict | None) -> int | None:
    if not slides or not quote:
        return slide_ids[0] if slide_ids else None
    brand = str(quote.get("default_slide_brand") or "")
    model = str(quote.get("default_slide_model") or "")
    code = str(quote.get("default_slide_code") or "")
    for slide in slides:
        if str(slide["brand"]) == brand and str(slide["model"]) == model and str(slide["code"]) == code:
            return int(slide["id"])
    return slide_ids[0] if slide_ids else None


def hinge_id_from_quote(hinges: list[dict], hinge_ids: list[int], quote: dict | None) -> int | None:
    if not hinges or not quote:
        return hinge_ids[0] if hinge_ids else None
    brand = str(quote.get("default_hinge_brand") or "")
    model = str(quote.get("default_hinge_model") or "")
    code = str(quote.get("default_hinge_code") or "")
    for hinge in hinges:
        if str(hinge["brand"]) == brand and str(hinge["model"]) == model and str(hinge["code"]) == code:
            return int(hinge["id"])
    return hinge_ids[0] if hinge_ids else None


def handle_id_from_quote(handles: list[dict], handle_ids: list[int], quote: dict | None, prefix: str) -> int | None:
    if not handles or not quote:
        return handle_ids[0] if handle_ids else None
    name = str(quote.get(f"default_{prefix}_handle_name") or "")
    supplier = str(quote.get(f"default_{prefix}_handle_supplier") or "")
    code = str(quote.get(f"default_{prefix}_handle_code") or "")
    for handle in handles:
        if str(handle["name"]) == name and str(handle["supplier"]) == supplier and str(handle["code"]) == code:
            return int(handle["id"])
    return handle_ids[0] if handle_ids else None
