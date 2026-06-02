import type { CSSProperties } from 'react'

export type ColourTheme =
  | 'neutral'
  | 'slate'
  | 'gray'
  | 'zinc'
  | 'stone'
  | 'olive'
  | 'red'
  | 'orange'
  | 'amber'
  | 'yellow'
  | 'lime'
  | 'green'
  | 'emerald'
  | 'teal'
  | 'cyan'
  | 'sky'
  | 'blue'
  | 'indigo'
  | 'violet'
  | 'purple'
  | 'mauve'
  | 'fuchsia'
  | 'pink'
  | 'rose'

export type ThemeMode = 'light' | 'dark'
export type UiStyle = 'vega' | 'nova' | 'maia' | 'lyra' | 'mira' | 'luma' | 'sera'

export type ThemeSpec = {
  chroma: number
  hue: number
  label: string
  value: ColourTheme
}

export type UiStyleSpec = {
  description: string
  label: string
  radius: 'locked' | 'soft' | 'balanced' | 'compact'
  value: UiStyle
}

export type ThemeVars = CSSProperties & Record<`--${string}`, string>
