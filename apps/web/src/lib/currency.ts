export const DEFAULT_CURRENCY_CODE = 'ZAR'

export type CurrencyOption = {
  code: string
  label: string
}

export const currencyOptions: CurrencyOption[] = [
  { code: 'ZAR', label: 'ZAR - South African rand' },
  { code: 'USD', label: 'USD - US dollar' },
  { code: 'GBP', label: 'GBP - Pound sterling' },
  { code: 'EUR', label: 'EUR - Euro' },
  { code: 'AUD', label: 'AUD - Australian dollar' },
  { code: 'CAD', label: 'CAD - Canadian dollar' },
  { code: 'NZD', label: 'NZD - New Zealand dollar' },
  { code: 'BWP', label: 'BWP - Botswana pula' },
  { code: 'NAD', label: 'NAD - Namibian dollar' },
  { code: 'MUR', label: 'MUR - Mauritian rupee' },
  { code: 'KES', label: 'KES - Kenyan shilling' },
  { code: 'NGN', label: 'NGN - Nigerian naira' },
  { code: 'AED', label: 'AED - UAE dirham' },
  { code: 'INR', label: 'INR - Indian rupee' },
  { code: 'JPY', label: 'JPY - Japanese yen' },
]

const currencyLocales: Record<string, string> = {
  AED: 'en-AE',
  AUD: 'en-AU',
  BWP: 'en-BW',
  CAD: 'en-CA',
  EUR: 'en-IE',
  GBP: 'en-GB',
  INR: 'en-IN',
  JPY: 'ja-JP',
  KES: 'en-KE',
  MUR: 'en-MU',
  NAD: 'en-NA',
  NGN: 'en-NG',
  NZD: 'en-NZ',
  USD: 'en-US',
  ZAR: 'en-ZA',
}

export function normalizeCurrencyCode(value: string | null | undefined) {
  const code = (value || DEFAULT_CURRENCY_CODE).trim().toUpperCase()
  return /^[A-Z]{3}$/.test(code) ? code : DEFAULT_CURRENCY_CODE
}

export function currencyLabel(value: string | null | undefined) {
  const code = normalizeCurrencyCode(value)
  return currencyOptions.find((option) => option.code === code)?.label ?? code
}

export function optionsForCurrency(value: string | null | undefined) {
  const code = normalizeCurrencyCode(value)
  if (currencyOptions.some((option) => option.code === code)) {
    return currencyOptions
  }
  return [{ code, label: code }, ...currencyOptions]
}

export function formatCurrencyFromCents(cents: number | null, currencyCode = DEFAULT_CURRENCY_CODE) {
  if (cents == null) return '-'
  const code = normalizeCurrencyCode(currencyCode)
  const locale = currencyLocales[code]
  try {
    return new Intl.NumberFormat(locale, {
      currency: code,
      style: 'currency',
    }).format((cents || 0) / 100)
  } catch {
    return new Intl.NumberFormat(currencyLocales[DEFAULT_CURRENCY_CODE], {
      currency: DEFAULT_CURRENCY_CODE,
      style: 'currency',
    }).format((cents || 0) / 100)
  }
}
