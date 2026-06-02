import type { ThemeMode, ThemeSpec, ThemeVars, UiStyle, UiStyleSpec } from '@/types/theme'

export const colourThemes: ThemeSpec[] = [
  { label: 'Neutral', value: 'neutral', chroma: 0.004, hue: 247 },
  { label: 'Slate', value: 'slate', chroma: 0.018, hue: 255 },
  { label: 'Gray', value: 'gray', chroma: 0.006, hue: 247 },
  { label: 'Zinc', value: 'zinc', chroma: 0.008, hue: 286 },
  { label: 'Stone', value: 'stone', chroma: 0.014, hue: 70 },
  { label: 'Olive', value: 'olive', chroma: 0.07, hue: 128 },
  { label: 'Red', value: 'red', chroma: 0.18, hue: 28 },
  { label: 'Orange', value: 'orange', chroma: 0.16, hue: 52 },
  { label: 'Amber', value: 'amber', chroma: 0.14, hue: 75 },
  { label: 'Yellow', value: 'yellow', chroma: 0.12, hue: 95 },
  { label: 'Lime', value: 'lime', chroma: 0.13, hue: 128 },
  { label: 'Green', value: 'green', chroma: 0.13, hue: 145 },
  { label: 'Emerald', value: 'emerald', chroma: 0.13, hue: 164 },
  { label: 'Teal', value: 'teal', chroma: 0.12, hue: 180 },
  { label: 'Cyan', value: 'cyan', chroma: 0.12, hue: 205 },
  { label: 'Sky', value: 'sky', chroma: 0.13, hue: 235 },
  { label: 'Blue', value: 'blue', chroma: 0.14, hue: 255 },
  { label: 'Indigo', value: 'indigo', chroma: 0.13, hue: 275 },
  { label: 'Violet', value: 'violet', chroma: 0.14, hue: 295 },
  { label: 'Purple', value: 'purple', chroma: 0.14, hue: 310 },
  { label: 'Mauve', value: 'mauve', chroma: 0.08, hue: 325 },
  { label: 'Fuchsia', value: 'fuchsia', chroma: 0.15, hue: 330 },
  { label: 'Pink', value: 'pink', chroma: 0.15, hue: 350 },
  { label: 'Rose', value: 'rose', chroma: 0.16, hue: 15 },
]

export const uiStyles: UiStyleSpec[] = [
  { label: 'Vega', value: 'vega', description: 'Classic shadcn baseline with balanced spacing.', radius: 'balanced' },
  { label: 'Nova', value: 'nova', description: 'Reduced padding and margins for compact layouts.', radius: 'compact' },
  { label: 'Maia', value: 'maia', description: 'Soft and rounded with generous spacing.', radius: 'soft' },
  { label: 'Lyra', value: 'lyra', description: 'Boxy, sharp, and structured for precise tools.', radius: 'locked' },
  { label: 'Mira', value: 'mira', description: 'Dense and product-focused for operational screens.', radius: 'compact' },
  { label: 'Luma', value: 'luma', description: 'Rounded geometry, soft elevation, and calmer rhythm.', radius: 'soft' },
  { label: 'Sera', value: 'sera', description: 'Structured editorial feel with crisp surfaces.', radius: 'locked' },
]

export function createThemeVars(theme: ThemeSpec, mode: ThemeMode, uiStyle: UiStyle): ThemeVars {
  const { chroma, hue, value } = theme
  const neutralTone = value === 'gray' || value === 'neutral' || value === 'zinc' || value === 'slate'
  const warmNeutral = value === 'stone'
  const primaryLightness = value === 'yellow' || value === 'amber' || value === 'lime' ? 0.34 : 0.39
  const primaryChroma = neutralTone ? chroma : chroma * 0.72
  const accentChroma = neutralTone ? chroma * 1.5 : chroma
  const foregroundChroma = warmNeutral ? 0.014 : chroma
  const primary = `oklch(${primaryLightness} ${primaryChroma} ${hue})`
  const darkPrimary = `oklch(${neutralTone ? 0.76 : 0.72} ${neutralTone ? chroma * 2 : primaryChroma} ${hue})`

  const lightTokens = {
    accent: `oklch(0.56 ${accentChroma} ${hue})`,
    'accent-foreground': 'oklch(0.985 0.003 247)',
    background: `oklch(0.985 ${neutralTone ? 0.002 : 0.008} ${hue})`,
    border: `oklch(0.82 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    card: 'oklch(1 0 0)',
    'card-foreground': `oklch(0.18 ${foregroundChroma} ${hue})`,
    destructive: 'oklch(0.56 0.18 28)',
    'destructive-foreground': 'oklch(0.985 0.003 247)',
    foreground: `oklch(0.18 ${foregroundChroma} ${hue})`,
    input: `oklch(0.82 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    muted: `oklch(0.95 ${neutralTone ? chroma : chroma * 0.1} ${hue})`,
    'muted-foreground': `oklch(0.45 ${neutralTone ? chroma : chroma * 0.28} ${hue})`,
    popover: 'oklch(1 0 0)',
    'popover-foreground': `oklch(0.18 ${foregroundChroma} ${hue})`,
    primary,
    'primary-foreground': 'oklch(0.985 0.003 247)',
    ring: `oklch(0.52 ${neutralTone ? chroma : chroma * 0.72} ${hue})`,
    secondary: `oklch(0.935 ${neutralTone ? chroma : chroma * 0.12} ${hue})`,
    'secondary-foreground': `oklch(0.23 ${neutralTone ? chroma : chroma * 0.32} ${hue})`,
    sidebar: `oklch(0.958 ${neutralTone ? chroma : chroma * 0.12} ${hue})`,
    'sidebar-accent': `oklch(0.9 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'status-success': 'oklch(0.965 0.035 158)',
    'status-success-border': 'oklch(0.78 0.12 158)',
    'status-success-foreground': 'oklch(0.38 0.11 158)',
    'status-warning': 'oklch(0.965 0.04 82)',
    'status-warning-border': 'oklch(0.82 0.11 82)',
    'status-warning-foreground': 'oklch(0.43 0.1 72)',
  }

  const darkTokens = {
    accent: darkPrimary,
    'accent-foreground': `oklch(0.16 ${foregroundChroma} ${hue})`,
    background: `oklch(0.15 ${neutralTone ? chroma : chroma * 0.18} ${hue})`,
    border: `oklch(0.32 ${neutralTone ? chroma : chroma * 0.24} ${hue})`,
    card: `oklch(0.19 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'card-foreground': `oklch(0.95 ${neutralTone ? chroma : chroma * 0.08} ${hue})`,
    destructive: 'oklch(0.66 0.16 28)',
    'destructive-foreground': 'oklch(0.985 0.003 247)',
    foreground: `oklch(0.95 ${neutralTone ? chroma : chroma * 0.08} ${hue})`,
    input: `oklch(0.34 ${neutralTone ? chroma : chroma * 0.24} ${hue})`,
    muted: `oklch(0.25 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'muted-foreground': `oklch(0.72 ${neutralTone ? chroma : chroma * 0.14} ${hue})`,
    popover: `oklch(0.2 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'popover-foreground': `oklch(0.95 ${neutralTone ? chroma : chroma * 0.08} ${hue})`,
    primary: darkPrimary,
    'primary-foreground': `oklch(0.15 ${foregroundChroma} ${hue})`,
    ring: darkPrimary,
    secondary: `oklch(0.27 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'secondary-foreground': `oklch(0.94 ${neutralTone ? chroma : chroma * 0.08} ${hue})`,
    sidebar: `oklch(0.13 ${neutralTone ? chroma : chroma * 0.18} ${hue})`,
    'sidebar-accent': `oklch(0.25 ${neutralTone ? chroma : chroma * 0.2} ${hue})`,
    'status-success': 'oklch(0.24 0.055 158)',
    'status-success-border': 'oklch(0.46 0.12 158)',
    'status-success-foreground': 'oklch(0.84 0.12 158)',
    'status-warning': 'oklch(0.25 0.055 82)',
    'status-warning-border': 'oklch(0.5 0.12 82)',
    'status-warning-foreground': 'oklch(0.86 0.13 82)',
  }

  const tokens = {
    ...(mode === 'dark' ? darkTokens : lightTokens),
    ...styleTokens(uiStyle),
  }

  return Object.entries(tokens).reduce<ThemeVars>((vars, [name, color]) => {
    vars[`--${name}`] = color
    vars[`--color-${name}`] = color
    return vars
  }, {})
}

function styleTokens(uiStyle: UiStyle) {
  const styles: Record<UiStyle, Record<string, string>> = {
    luma: {
      'card-padding': '1.375rem',
      'card-radius': '1rem',
      'control-height': '2.5rem',
      'control-padding-x': '0.9rem',
      'control-radius': '0.875rem',
      'radius-lg-global': '1rem',
      'radius-md-global': '0.875rem',
      'radius-sm-global': '0.625rem',
      'section-gap': '1.25rem',
      'shadow-card': '0 14px 30px rgb(0 0 0 / 0.08)',
    },
    lyra: {
      'card-padding': '1rem',
      'card-radius': '0rem',
      'control-height': '2.25rem',
      'control-padding-x': '0.75rem',
      'control-radius': '0rem',
      'radius-lg-global': '0rem',
      'radius-md-global': '0rem',
      'radius-sm-global': '0rem',
      'section-gap': '1rem',
      'shadow-card': 'none',
    },
    maia: {
      'card-padding': '1.5rem',
      'card-radius': '1.25rem',
      'control-height': '2.5rem',
      'control-padding-x': '1rem',
      'control-radius': '999px',
      'radius-lg-global': '1.25rem',
      'radius-md-global': '1rem',
      'radius-sm-global': '0.75rem',
      'section-gap': '1.5rem',
      'shadow-card': '0 10px 28px rgb(0 0 0 / 0.06)',
    },
    mira: {
      'card-padding': '0.875rem',
      'card-radius': '0.25rem',
      'control-height': '2rem',
      'control-padding-x': '0.625rem',
      'control-radius': '0.25rem',
      'radius-lg-global': '0.375rem',
      'radius-md-global': '0.25rem',
      'radius-sm-global': '0.125rem',
      'section-gap': '0.75rem',
      'shadow-card': '0 1px 0 rgb(0 0 0 / 0.05)',
    },
    nova: {
      'card-padding': '0.95rem',
      'card-radius': '0.375rem',
      'control-height': '2.125rem',
      'control-padding-x': '0.7rem',
      'control-radius': '0.375rem',
      'radius-lg-global': '0.5rem',
      'radius-md-global': '0.375rem',
      'radius-sm-global': '0.25rem',
      'section-gap': '0.875rem',
      'shadow-card': '0 1px 0 rgb(0 0 0 / 0.04)',
    },
    sera: {
      'card-padding': '1.125rem',
      'card-radius': '0.125rem',
      'control-height': '2.25rem',
      'control-padding-x': '0.85rem',
      'control-radius': '0.125rem',
      'radius-lg-global': '0.125rem',
      'radius-md-global': '0.125rem',
      'radius-sm-global': '0.0625rem',
      'section-gap': '1.125rem',
      'shadow-card': '0 0 0 1px rgb(0 0 0 / 0.02)',
    },
    vega: {
      'card-padding': '1rem',
      'card-radius': '0.5rem',
      'control-height': '2.25rem',
      'control-padding-x': '0.75rem',
      'control-radius': '0.5rem',
      'radius-lg-global': '0.5rem',
      'radius-md-global': '0.5rem',
      'radius-sm-global': '0.25rem',
      'section-gap': '1rem',
      'shadow-card': '0 1px 2px rgb(0 0 0 / 0.06)',
    },
  }

  return styles[uiStyle]
}
