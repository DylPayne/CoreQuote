from logic.models import Board, Slide

class BaseUnit:
    def __init__(self, h, w, d, thickness=16):
        self.h = h
        self.w = w
        self.d = d
        self.t = thickness

    def get_carcass_list(self) -> list[Board]:
        return [
            Board("Side", self.h-(2*self.t), self.d-self.t, 2),
            Board("Base", self.w, self.d, 1),
            Board("Rail", self.w, 100, 2),
            Board("Backing", self.h-(2*self.t), self.w, 1)
        ]
    
class DrawerUnit(BaseUnit):
    # TODO: Add slide selection functionality

    def __init__(self, h, w, d, slide: Slide, num_drawers=3, thickness=16):
        super().__init__(h, w, d, thickness)
        self.num_drawers = num_drawers
        self.slide = slide

    def get_carcass_list(self):
        # Get base carcass boards
        boards = super().get_carcass_list()

        drawer_depth = self.slide.side_length
        # This is intertnal drawer width
        drawer_width = self.w-self.slide.side_clearance_total
        drawer_side_rebate = 10

        # Get drawer carcass boards
        # TODO: Replace draw carcass side and front dimensions based on selected slide
        # TODO: Add functionality to modify drawer side rebate by adjusting drawer base
        boards.append(Board("Drawer Side", drawer_depth, 200, 2*self.num_drawers))
        boards.append(Board("Drawer Front/Back", drawer_width, 174, 2*self.num_drawers))
        boards.append(Board("Drawer Base", drawer_width+drawer_side_rebate, drawer_depth, self.num_drawers))

        return boards

class DoorUnit(BaseUnit):
    def __init__(self, h, w, d, num_doors=2, num_shelves=1, thickness=16):
        super().__init__(h, w, d, thickness)
        self.num_doors = num_doors
        self.num_shelves = num_shelves

    def get_carcass_list(self):
        boards = super().get_carcass_list()

        shelf_setback = 20

        boards.append(Board("Shelf", self.w-(2*self.t), self.d-self.t-shelf_setback, self.num_shelves))

        return boards