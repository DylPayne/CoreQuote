from __future__ import annotations


def format_board_label(board: dict) -> str:
    return f"{board['brand']} • {board['material']} • {board['thickness']}mm • {board['length_mm']}x{board['width_mm']}"


def format_slide_label(slide: dict) -> str:
    return f"{slide['brand']} {slide['model']} ({int(slide['length'])}mm)"


def format_hinge_label(hinge: dict) -> str:
    return f"{hinge['brand']} {hinge['model']} ({int(hinge['opening_angle_deg'])}°)"


def format_handle_label(handle: dict) -> str:
    name = str(handle.get("name", "")).strip()
    supplier = str(handle.get("supplier", "")).strip()
    code = str(handle.get("code", "")).strip()
    label = name or "Handle"
    if supplier:
        label += f" • {supplier}"
    if code:
        label += f" • {code}"
    return label


def format_extra_category_label(category: dict) -> str:
    return str(category.get("name", "")).strip() or "Category"


def format_extra_label(extra: dict) -> str:
    name = str(extra.get("name", "")).strip()
    category = str(extra.get("category_name", extra.get("category", ""))).strip()
    supplier = str(extra.get("supplier", "")).strip()
    code = str(extra.get("code", "")).strip()
    label = name or "Extra"
    if category:
        label += f" • {category}"
    if supplier:
        label += f" • {supplier}"
    if code:
        label += f" • {code}"
    return label
