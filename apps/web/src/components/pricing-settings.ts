export type PricingSettingsValues = {
  vat_rate_bps: number
  default_markup_bps: number
  carcass_markup_bps: number
  door_panel_markup_bps: number
  component_markup_bps: number
  handle_markup_bps: number
  extras_markup_bps: number
  fabrication_markup_bps: number
  install_markup_bps: number
  delivery_markup_bps: number
  joinery_commission_bps: number
  labour_cents_per_m2: number
  consumables_cents_per_m2: number
  install_day_cost_cents: number
  delivery_base_cents: number
  install_units_per_day: number
  delivery_units_per_trip: number
  minimum_install_days_bps: number
  minimum_delivery_trips_bps: number
}

export type PricingSettingsDraft = Record<keyof PricingSettingsValues, string>

export type CompanyPricingSettingsRow = PricingSettingsValues & {
  company_id: string
  created_at: string
  updated_at: string
}

export type ProjectPricingSettingsRow = CompanyPricingSettingsRow & {
  project_id: string
}

export type QuotePricingSettingsRow = CompanyPricingSettingsRow & {
  quote_id: string
}

export const defaultPricingSettingsDraft: PricingSettingsDraft = {
  vat_rate_bps: '15.00',
  default_markup_bps: '25.00',
  carcass_markup_bps: '25.00',
  door_panel_markup_bps: '25.00',
  component_markup_bps: '25.00',
  handle_markup_bps: '25.00',
  extras_markup_bps: '25.00',
  fabrication_markup_bps: '25.00',
  install_markup_bps: '25.00',
  delivery_markup_bps: '25.00',
  joinery_commission_bps: '0.00',
  labour_cents_per_m2: '20.00',
  consumables_cents_per_m2: '10.00',
  install_day_cost_cents: '1900.00',
  delivery_base_cents: '950.00',
  install_units_per_day: '3',
  delivery_units_per_trip: '20',
  minimum_install_days_bps: '0.50',
  minimum_delivery_trips_bps: '0.50',
}

export const pricingPercentFields = [
  { key: 'vat_rate_bps', label: 'VAT (%)' },
  { key: 'default_markup_bps', label: 'Default markup (%)' },
  { key: 'joinery_commission_bps', label: 'Joinery commission (%)' },
] as const

export const pricingMarkupFields = [
  { key: 'carcass_markup_bps', label: 'Carcass material (%)' },
  { key: 'door_panel_markup_bps', label: 'Doors and panels (%)' },
  { key: 'component_markup_bps', label: 'Components (%)' },
  { key: 'handle_markup_bps', label: 'Handles (%)' },
  { key: 'extras_markup_bps', label: 'Extras (%)' },
  { key: 'fabrication_markup_bps', label: 'Fabrication (%)' },
  { key: 'install_markup_bps', label: 'Installation (%)' },
  { key: 'delivery_markup_bps', label: 'Delivery (%)' },
] as const

export const pricingMoneyFields = [
  { key: 'labour_cents_per_m2', label: 'Labour per m2' },
  { key: 'consumables_cents_per_m2', label: 'Consumables per m2' },
  { key: 'install_day_cost_cents', label: 'Install day cost' },
  { key: 'delivery_base_cents', label: 'Delivery base' },
] as const

export const pricingQuantityFields = [
  { key: 'install_units_per_day', label: 'Units per install day' },
  { key: 'delivery_units_per_trip', label: 'Units per delivery' },
] as const

export const pricingMinimumFields = [
  { key: 'minimum_install_days_bps', label: 'Minimum install days' },
  { key: 'minimum_delivery_trips_bps', label: 'Minimum deliveries' },
] as const

export function pricingSettingsToDraft(settings: PricingSettingsValues): PricingSettingsDraft {
  return {
    vat_rate_bps: bpsToPercentString(settings.vat_rate_bps),
    default_markup_bps: bpsToPercentString(settings.default_markup_bps),
    carcass_markup_bps: bpsToPercentString(settings.carcass_markup_bps),
    door_panel_markup_bps: bpsToPercentString(settings.door_panel_markup_bps),
    component_markup_bps: bpsToPercentString(settings.component_markup_bps),
    handle_markup_bps: bpsToPercentString(settings.handle_markup_bps),
    extras_markup_bps: bpsToPercentString(settings.extras_markup_bps),
    fabrication_markup_bps: bpsToPercentString(settings.fabrication_markup_bps),
    install_markup_bps: bpsToPercentString(settings.install_markup_bps),
    delivery_markup_bps: bpsToPercentString(settings.delivery_markup_bps),
    joinery_commission_bps: bpsToPercentString(settings.joinery_commission_bps),
    labour_cents_per_m2: centsToAmountString(settings.labour_cents_per_m2),
    consumables_cents_per_m2: centsToAmountString(settings.consumables_cents_per_m2),
    install_day_cost_cents: centsToAmountString(settings.install_day_cost_cents),
    delivery_base_cents: centsToAmountString(settings.delivery_base_cents),
    install_units_per_day: String(settings.install_units_per_day),
    delivery_units_per_trip: String(settings.delivery_units_per_trip),
    minimum_install_days_bps: decimalBpsToString(settings.minimum_install_days_bps),
    minimum_delivery_trips_bps: decimalBpsToString(settings.minimum_delivery_trips_bps),
  }
}

export function pricingSettingsPayloadFromDraft(draft: PricingSettingsDraft): PricingSettingsValues | null {
  const payload = {
    vat_rate_bps: percentStringToBps(draft.vat_rate_bps),
    default_markup_bps: percentStringToBps(draft.default_markup_bps),
    carcass_markup_bps: percentStringToBps(draft.carcass_markup_bps),
    door_panel_markup_bps: percentStringToBps(draft.door_panel_markup_bps),
    component_markup_bps: percentStringToBps(draft.component_markup_bps),
    handle_markup_bps: percentStringToBps(draft.handle_markup_bps),
    extras_markup_bps: percentStringToBps(draft.extras_markup_bps),
    fabrication_markup_bps: percentStringToBps(draft.fabrication_markup_bps),
    install_markup_bps: percentStringToBps(draft.install_markup_bps),
    delivery_markup_bps: percentStringToBps(draft.delivery_markup_bps),
    joinery_commission_bps: percentStringToBps(draft.joinery_commission_bps),
    labour_cents_per_m2: amountStringToCents(draft.labour_cents_per_m2),
    consumables_cents_per_m2: amountStringToCents(draft.consumables_cents_per_m2),
    install_day_cost_cents: amountStringToCents(draft.install_day_cost_cents),
    delivery_base_cents: amountStringToCents(draft.delivery_base_cents),
    install_units_per_day: positiveWholeNumber(draft.install_units_per_day),
    delivery_units_per_trip: positiveWholeNumber(draft.delivery_units_per_trip),
    minimum_install_days_bps: decimalStringToBps(draft.minimum_install_days_bps),
    minimum_delivery_trips_bps: decimalStringToBps(draft.minimum_delivery_trips_bps),
  }

  if (Object.values(payload).some((value) => value === null)) {
    return null
  }
  return payload as PricingSettingsValues
}

function centsToAmountString(cents: number) {
  return ((cents || 0) / 100).toFixed(2)
}

function amountStringToCents(value: string): number | null {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.round(parsed * 100)
}

function bpsToPercentString(bps: number) {
  return (bps / 100).toFixed(2)
}

function percentStringToBps(value: string): number | null {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.round(parsed * 100)
}

function decimalBpsToString(value: number) {
  return (value / 10000).toFixed(2)
}

function decimalStringToBps(value: string) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.round(parsed * 10000)
}

function positiveWholeNumber(value: string) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) return null
  return Math.floor(parsed)
}
