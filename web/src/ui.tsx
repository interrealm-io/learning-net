import type { ReactNode } from 'react'
import { standardHref } from './router'
import type { Brief } from './types'

export const fmt = (n: number) => n.toLocaleString('en-US')

export function grades(g?: string) {
  if (!g) return null
  return (g.includes(',') ? 'Grades ' : 'Grade ') + g
}

export function CodeChip({ code }: { code?: string }) {
  return code ? <span className="code-chip">{code}</span> : null
}

// The tag row renders a standard's identity. Multi-State wears brass — the one
// color this app reserves for the spine and anything inferred through it.
export function Tags({ s }: { s: Brief }) {
  return (
    <span className="tags">
      <CodeChip code={s.statementCode} />
      {s.label !== 'StandardsFrameworkItem' && <span className="tag tag-quiet">{s.label}</span>}
      {s.jurisdiction && (
        <span className={s.jurisdiction === 'Multi-State' ? 'tag tag-spine' : 'tag'}>
          {s.jurisdiction}
        </span>
      )}
      {s.gradeLevel && <span className="tag">{grades(s.gradeLevel)}</span>}
      {s.subject && <span className="tag tag-quiet">{s.subject}</span>}
    </span>
  )
}

export function StandardEntry({ s }: { s: Brief }) {
  return (
    <a className="entry" href={standardHref(s.id)}>
      <Tags s={s} />
      {s.statement && <p className="statement">{s.statement}</p>}
    </a>
  )
}

export function SpineBadge({ on }: { on?: boolean }) {
  if (!on) return null
  return (
    <span
      className="spine-badge"
      title="This answer crossed the Multi-State spine: it was found through alignment, not authored on this standard."
    >
      inferred via Multi-State spine
    </span>
  )
}

export function Note({ text }: { text?: string }) {
  return text ? <p className="note">{text}</p> : null
}

export function Loading() {
  return (
    <p className="quiet" role="status">
      Loading…
    </p>
  )
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <p className="error" role="alert">
      {message}
    </p>
  )
}

export function Section({
  title,
  aside,
  children,
}: {
  title: string
  aside?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="section">
      <div className="section-head">
        <h2>{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}
