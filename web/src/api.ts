import { useEffect, useState } from 'react'
import type {
  ComponentsResult,
  ContextResult,
  CoverageReport,
  CrosswalkResult,
  CurriculumResult,
  FindResult,
  ProgressionResult,
  SearchResult,
  Stats,
} from './types'

async function call<T>(
  tool: string,
  params: Record<string, string | number | undefined> = {},
): Promise<T> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') qs.set(k, String(v))
  }
  let r: Response
  try {
    r = await fetch(`/api/${tool}${qs.size ? `?${qs}` : ''}`)
  } catch {
    throw new Error('Could not reach the mirror. Is `learning-net web` still running?')
  }
  if (!r.ok) {
    let msg = `Request failed (${r.status})`
    try {
      const body = (await r.json()) as { error?: string }
      if (body.error) msg = body.error
    } catch {
      // non-JSON error body; keep the status message
    }
    throw new Error(msg)
  }
  return r.json() as Promise<T>
}

export const findStandard = (code: string, jurisdiction?: string) =>
  call<FindResult>('find_standard', { statementCode: code, jurisdiction })

export const searchStandards = (p: {
  query: string
  jurisdiction?: string
  subject?: string
  gradeLevel?: string
}) => call<SearchResult>('search_standards', p)

export const learningComponents = (standard: string) =>
  call<ComponentsResult>('get_learning_components', { standard })

export const progression = (standard: string, direction: 'backward' | 'forward') =>
  call<ProgressionResult>('get_progression', { standard, direction })

export const crosswalk = (standard: string, toJurisdiction?: string) =>
  call<CrosswalkResult>('crosswalk_standard', { standard, toJurisdiction })

export const context = (standard: string) =>
  call<ContextResult>('get_standard_context', { standard })

export const curriculum = (standard: string) =>
  call<CurriculumResult>('find_curriculum', { standard })

export const coverageReport = (subject?: string) =>
  call<CoverageReport>('coverage_report', { subject })

// The mirror only changes on a rebuild, so stats are fetched once per page load
// and shared by the top bar, the search filters, and the status page. A failed
// fetch clears the memo so a transient outage doesn't poison the whole session.
let statsPromise: Promise<Stats> | undefined
export const stats = () =>
  (statsPromise ??= call<Stats>('graph_stats').catch((e: Error) => {
    statsPromise = undefined
    throw e
  }))

export interface Fetched<T> {
  data?: T
  error?: string
  loading: boolean
}

export function useApi<T>(fn: (() => Promise<T>) | null, deps: unknown[]): Fetched<T> {
  const [state, set] = useState<Fetched<T>>({ loading: fn !== null })
  useEffect(() => {
    if (!fn) {
      set({ loading: false })
      return
    }
    let live = true
    set({ loading: true })
    fn().then(
      (data) => {
        if (live) set({ data, loading: false })
      },
      (e: Error) => {
        if (live) set({ error: e.message, loading: false })
      },
    )
    return () => {
      live = false
    }
    // eslint-style exhaustive-deps is intentionally not wanted: deps is the contract
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps
  return state
}
