# logic.py

def get_cabinet_parts(height, width, depth, thickness):
    """
    Your custom rules for a standard base cabinet.
    """
    # Example: Subtracting thickness for a 'butt joint' construction
    sides_height = height
    bottom_width = width - (2 * thickness)
    
    return [
        {"Part": "Side (x2)", "L": sides_height, "W": depth},
        {"Part": "Bottom", "L": bottom_width, "W": depth},
        {"Part": "Top Rail (x2)", "L": bottom_width, "W": 100}, # 100mm rail
        {"Part": "Draw Base (x2)", "L": depth-thickness-10, "W": width-(thickness*2)-10+8},
        {"Part": "Draw Sides (x4)", "L": depth-thickness-10, "W": 200}
    ]

# def get_door_carcass_list(height, width, depth, thickness):
#     rails = 

def get_door_panel_list(height, width, num_doors):
    return [
        {"L": height, "W": width-3 if num_doors == 1 else width/2-3, "Qty": num_doors}
    ]

def get_draw_panel_list(height, width, num_draws):
    return [
        {"L": height, "W": width-3 if num_draws == 1 else width/num_draws-3, "Qty": num_draws}
    ]