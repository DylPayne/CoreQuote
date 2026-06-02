import type { ReactNode } from 'react'

import type { ColourTheme, ThemeMode, ThemeVars, UiStyle } from '@/types/theme'

export function AppTheme({
  children,
  colourTheme,
  themeMode,
  themeVars,
  uiStyle,
}: {
  children: ReactNode
  colourTheme: ColourTheme
  themeMode: ThemeMode
  themeVars: ThemeVars
  uiStyle: UiStyle
}) {
  return (
    <div
      className="min-h-screen bg-background text-foreground"
      data-mode={themeMode}
      data-style={uiStyle}
      data-theme={colourTheme}
      style={themeVars}
    >
      {children}
    </div>
  )
}
