// Shapes mirror graph.py's return values after server-side null-pruning:
// a field the graph reports as null simply never appears in the payload.

export interface Brief {
  id: string
  label: string
  statementCode?: string
  jurisdiction?: string
  subject?: string
  gradeLevel?: string
  statementType?: string
  caseIdentifierUUID?: string
  statement?: string
}

export interface FindResult {
  query: { statementCode: string; jurisdiction?: string; subject?: string }
  matchCount: number
  note?: string
  standards: Brief[]
}

export interface SearchResult {
  query: string
  resultCount: number
  results: Brief[]
}

export interface ComponentsResult {
  standard: Brief
  componentCount: number
  learningComponents: { id: string; component?: string; subject?: string }[]
}

export interface ProgressionEntry extends Brief {
  equivalentInJurisdiction?: Brief[]
}

export interface ProgressionResult {
  standard: Brief
  direction: 'backward' | 'forward'
  bridgedViaMultiState: boolean
  anchors?: Brief[]
  resultCount: number
  note?: string
  progression: ProgressionEntry[]
}

export interface CrosswalkResult {
  standard: Brief
  viaMultiStateHub: boolean
  alignmentCount: number
  note?: string
  alignedStandards: Brief[]
}

export interface ContextResult {
  standard: Brief
  ancestors: Brief[]
  childCount: number
  children: Brief[]
}

export interface CurriculumItem {
  id: string
  type: string
  name?: string
  gradeLevel?: string
  subject?: string
}

export interface CurriculumResult {
  standard: Brief
  bridgedViaMultiState: boolean
  itemCount: number
  note?: string
  curriculum: CurriculumItem[]
}

export interface Stats {
  nodesByLabel: Record<string, number>
  edgesByLabel: Record<string, number>
  jurisdictions: Record<string, number>
  subjects: Record<string, number>
  snapshot?: Record<string, string>
}

export interface CoverageRow {
  jurisdiction: string
  standards: number
  crosswalked: number
  crosswalkPct: number
  withComponents: number
  componentsPct: number
  withCurriculum: number
  withProgression: number
  isolated: boolean
}

export interface CoverageReport {
  subject?: string
  generatedFrom?: Record<string, string>
  national: {
    jurisdictions: number
    standards: number
    crosswalked: number
    crosswalkPct: number
    jurisdictionsWithNoCrosswalk: number
    isolatedJurisdictions: string[]
    standardsInIsolatedJurisdictions: number
    medianCrosswalkPctWhereAny: number
  }
  interpretation: string
  byJurisdiction: CoverageRow[]
}
