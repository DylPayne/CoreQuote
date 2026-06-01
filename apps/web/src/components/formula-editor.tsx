import CodeMirror from '@uiw/react-codemirror'
import { autocompletion, completeFromList, type Completion } from '@codemirror/autocomplete'
import { EditorView, keymap } from '@codemirror/view'
import { Maximize2, Minimize2 } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type FormulaEditorProps = {
  disabled?: boolean
  error?: string
  onBlur?: (value: string) => void
  onChange: (value: string) => void
  placeholder?: string
  suggestions: string[]
  value: string
}

const functionCompletions = ['abs', 'ceil', 'floor', 'if', 'max', 'min', 'round']
const keywordCompletions = ['and', 'or', 'not', 'true', 'false']

export function FormulaEditor({ disabled = false, error, onBlur, onChange, placeholder, suggestions, value }: FormulaEditorProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const completions = useMemo<Completion[]>(() => {
    const variableItems = suggestions.map((label) => ({ label, type: 'variable' as const }))
    const functionItems = functionCompletions.map((label) => ({
      apply: `${label}()`,
      label,
      type: 'function' as const,
    }))
    const keywordItems = keywordCompletions.map((label) => ({ label, type: 'keyword' as const }))
    return [...variableItems, ...functionItems, ...keywordItems]
  }, [suggestions])

  const sharedExtensions = useMemo(
    () => [
      EditorView.lineWrapping,
      autocompletion({
        activateOnTyping: true,
        override: [completeFromList(completions)],
      }),
      keymap.of([
        {
          key: 'Enter',
          preventDefault: true,
          run: () => true,
        },
      ]),
    ],
    [completions],
  )

  const inlineTheme = useMemo(
    () =>
      EditorView.theme({
        '&': {
          backgroundColor: 'transparent',
          fontSize: '0.875rem',
        },
        '.cm-content': {
          fontFamily: 'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace)',
          minHeight: '1.5rem',
          padding: '0.375rem 0.625rem',
        },
        '.cm-editor': {
          borderRadius: 'var(--control-radius)',
          minHeight: '2rem',
          outline: 'none',
        },
        '.cm-focused': {
          outline: 'none',
        },
        '.cm-scroller': {
          fontFamily: 'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace)',
        },
      }),
    [],
  )

  const expandedTheme = useMemo(
    () =>
      EditorView.theme({
        '&': {
          backgroundColor: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--card-radius)',
          fontSize: '0.95rem',
        },
        '.cm-content': {
          fontFamily: 'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace)',
          minHeight: '10rem',
          padding: '0.75rem',
        },
        '.cm-focused': {
          outline: 'none',
        },
        '.cm-scroller': {
          fontFamily: 'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace)',
        },
      }),
    [],
  )

  function handleValueChange(nextValue: string) {
    const normalized = nextValue.replace(/\n+/g, ' ')
    onChange(normalized)
  }

  return (
    <>
      <div
        aria-invalid={Boolean(error)}
        className={cn(
          'flex min-w-[220px] items-center rounded-[var(--control-radius)] border border-input bg-card shadow-[var(--shadow-card)] transition-colors hover:bg-muted',
          error ? 'border-destructive ring-1 ring-destructive' : '',
          disabled ? 'cursor-not-allowed opacity-50' : '',
        )}
        title={error ?? ''}
      >
        <div className="min-w-0 flex-1">
          <CodeMirror
            basicSetup={{
              foldGutter: false,
              highlightActiveLine: false,
              highlightActiveLineGutter: false,
              lineNumbers: false,
            }}
            editable={!disabled}
            extensions={[...sharedExtensions, inlineTheme]}
            onBlur={() => onBlur?.(value)}
            onChange={handleValueChange}
            placeholder={placeholder}
            value={value}
          />
        </div>
        <Button
          className="h-8 rounded-l-none border-0 border-l border-border px-2"
          disabled={disabled}
          onClick={() => setIsExpanded(true)}
          size="icon"
          type="button"
          variant="ghost"
        >
          <Maximize2 className="h-3.5 w-3.5" aria-hidden="true" />
          <span className="sr-only">Expand formula editor</span>
        </Button>
      </div>

      {isExpanded ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-3xl rounded-[var(--card-radius)] border border-border bg-card p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-semibold">Formula editor</p>
              <Button onClick={() => setIsExpanded(false)} size="sm" type="button" variant="outline">
                <Minimize2 className="h-4 w-4" aria-hidden="true" />
                Collapse
              </Button>
            </div>
            <CodeMirror
              basicSetup={{
                lineNumbers: true,
              }}
              editable={!disabled}
              extensions={[...sharedExtensions, expandedTheme]}
              onBlur={() => onBlur?.(value)}
              onChange={handleValueChange}
              placeholder={placeholder}
              value={value}
            />
            {error ? <p className="mt-2 text-xs text-destructive">{error}</p> : null}
            <p className="mt-2 text-xs text-muted-foreground">Autocomplete supports variables, helpers, and logical keywords.</p>
          </div>
        </div>
      ) : null}
    </>
  )
}
