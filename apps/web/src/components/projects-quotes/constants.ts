import type { PanelPresetKey, ProjectDraft, QuoteDraft, UnitDefaults, UnitDraft, UnitPresetKey } from './types'

export const unitPresets: UnitPresetKey[] = ['Base Draw', 'Base Door', 'Wall Door', 'Tall Door']
export const customUnitTypeValue = '__custom_unit_type__'
export const panelPresetKeys: PanelPresetKey[] = [
  'base_side_panel',
  'base_side_filler',
  'wall_side_panel',
  'wall_side_filler',
  'tall_side_panel',
  'tall_side_filler',
]
export const panelPresetLabels: Record<PanelPresetKey, string> = {
  base_side_panel: 'Base Side Panel',
  base_side_filler: 'Base Side Filler',
  wall_side_panel: 'Wall Side Panel',
  wall_side_filler: 'Wall Side Filler',
  tall_side_panel: 'Tall Side Panel',
  tall_side_filler: 'Tall Side Filler',
}
export const panelPresetFamily: Record<PanelPresetKey, 'base' | 'wall' | 'tall'> = {
  base_side_panel: 'base',
  base_side_filler: 'base',
  wall_side_panel: 'wall',
  wall_side_filler: 'wall',
  tall_side_panel: 'tall',
  tall_side_filler: 'tall',
}

export const fallbackUnitDefaults: UnitDefaults = {
  'Base Draw': { height: 780, depth: 580 },
  'Base Door': { height: 780, depth: 580 },
  'Wall Door': { height: 720, depth: 330 },
  'Tall Door': { height: 2100, depth: 580 },
}

export const defaultProjectDraft: ProjectDraft = {
  name: '',
  client: '',
  address: '',
  description: '',
}

export const defaultQuoteDraft: QuoteDraft = {
  name: '',
  notes: '',
  default_carcass_board_type_id: '',
  default_door_board_type_id: '',
  default_panel_board_type_id: '',
  default_slide_id: '',
  default_hinge_id: '',
  default_base_handle_id: '',
  default_wall_handle_id: '',
  default_tall_handle_id: '',
  default_drawer_handle_id: '',
  base_draw_height: String(fallbackUnitDefaults['Base Draw'].height),
  base_draw_depth: String(fallbackUnitDefaults['Base Draw'].depth),
  base_door_height: String(fallbackUnitDefaults['Base Door'].height),
  base_door_depth: String(fallbackUnitDefaults['Base Door'].depth),
  wall_door_height: String(fallbackUnitDefaults['Wall Door'].height),
  wall_door_depth: String(fallbackUnitDefaults['Wall Door'].depth),
  tall_door_height: String(fallbackUnitDefaults['Tall Door'].height),
  tall_door_depth: String(fallbackUnitDefaults['Tall Door'].depth),
}

export const defaultUnitDraft: UnitDraft = {
  unit_type_key: 'Base Draw',
  custom_unit_type_key: '',
  height: String(fallbackUnitDefaults['Base Draw'].height),
  width: '600',
  depth: String(fallbackUnitDefaults['Base Draw'].depth),
  thickness: '16',
  carcass_board_type_id: '',
  door_board_type_id: '',
  num_drawers: '3',
  num_doors: '2',
  num_shelves: '1',
}
