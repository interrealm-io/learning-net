import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { standardHref } from './router'
import type { Brief } from './types'

export const fmt = (n: number) => n.toLocaleString('en-US')

export function grades(g?: string) {
  if (!g) return null
  return (g.includes(',') ? 'Grades ' : 'Grade ') + g
}

/* ---- page furniture ----------------------------------------------------- */

export function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="eyebrow">{children}</p>
}

export function PageHead({
  eyebrow,
  title,
  lede,
  children,
}: {
  eyebrow: string
  title: ReactNode
  lede?: ReactNode
  children?: ReactNode
}) {
  return (
    <header className="page-head">
      <Eyebrow>{eyebrow}</Eyebrow>
      <h1 className="h1">{title}</h1>
      {lede && <p className="lede">{lede}</p>}
      {children}
    </header>
  )
}

export function Section({
  title,
  aside,
  id,
  children,
}: {
  title: string
  aside?: ReactNode
  id?: string
  children: ReactNode
}) {
  return (
    <section className="section" id={id}>
      <div className="section-head">
        <h2 className="label">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

/* ---- identity ----------------------------------------------------------- */

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

export function StandardEntry({ s, cursor }: { s: Brief; cursor?: boolean }) {
  const el = useRef<HTMLAnchorElement>(null)
  useEffect(() => {
    if (cursor) el.current?.scrollIntoView({ block: 'nearest' })
  }, [cursor])
  return (
    <a
      ref={el}
      className={cursor ? 'entry entry-cursor' : 'entry'}
      href={standardHref(s.id)}
      data-cursor={cursor || undefined}
    >
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

/* ---- state -------------------------------------------------------------- */

export function Note({ text }: { text?: string }) {
  return text ? <p className="note">{text}</p> : null
}

// A determinate-looking bar rather than a spinner: it occupies a fixed 2px of
// height, so results arriving never shove the page down.
export function Loading({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="loading-bar" role="status" aria-label={label}>
      <span />
    </div>
  )
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <p className="error" role="alert">
      {message}
    </p>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {children}
    </div>
  )
}

/* ---- code + copy -------------------------------------------------------- */

export function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [done, setDone] = useState(false)
  return (
    <button
      type="button"
      className={done ? 'copy copy-done' : 'copy'}
      onClick={() => {
        // Clipboard access is refused on plain-HTTP origins other than
        // localhost; a district serving this over http:// on a LAN address
        // must still get the text, so fall back to a hidden selection.
        const ok = () => {
          setDone(true)
          setTimeout(() => setDone(false), 1600)
        }
        navigator.clipboard?.writeText(text).then(ok, () => {
          const ta = document.createElement('textarea')
          ta.value = text
          ta.style.position = 'fixed'
          ta.style.opacity = '0'
          document.body.append(ta)
          ta.select()
          try {
            document.execCommand('copy')
            ok()
          } finally {
            ta.remove()
          }
        })
      }}
    >
      {done ? 'Copied' : label}
    </button>
  )
}

export function CodeBlock({ code, copy = true }: { code: string; copy?: boolean }) {
  return (
    <div className="code">
      {copy && <CopyButton text={code} />}
      <pre>{code}</pre>
    </div>
  )
}
