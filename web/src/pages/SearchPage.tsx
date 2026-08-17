import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { findStandard, searchStandards, stats, useApi } from '../api'
import { useCursor, useDebounced } from '../hooks'
import { navigate, standardHref } from '../router'
import { Empty, ErrorBox, fmt, Loading, Note, PageHead, StandardEntry } from '../ui'

const GRADES = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']

// A bare code like 4.OA.A.3 or HS-LS2-5 is one unspaced token with a digit and
// a separator; searching statements won't find it, so codes get a direct lookup.
const looksLikeCode = (q: string) => /^\S+$/.test(q) && /\d/.test(q) && /[.-]/.test(q)

interface Filters {
  jurisdiction: string
  subject: string
  grade: string
}

export function SearchPage({ params }: { params: URLSearchParams }) {
  const [q, setQ] = useState(params.get('q') ?? '')
  const [f, setF] = useState<Filters>({
    jurisdiction: params.get('jurisdiction') ?? '',
    subject: params.get('subject') ?? '',
    grade: params.get('grade') ?? '',
  })
  const query = useDebounced(q.trim())

  // The URL is the permalink, so it tracks the settled query — but with
  // replaceState, not a hash assignment: a hashchange would remount this page
  // and take the caret with it on every keystroke.
  useEffect(() => {
    const qs = new URLSearchParams()
    if (query) qs.set('q', query)
    for (const [k, v] of Object.entries(f)) if (v) qs.set(k, v)
    history.replaceState(null, '', `#/search${qs.size ? `?${qs}` : ''}`)
  }, [query, f])

  const st = useApi(stats, [])
  const results = useApi(
    query
      ? () =>
          searchStandards({
            query,
            jurisdiction: f.jurisdiction || undefined,
            subject: f.subject || undefined,
            gradeLevel: f.grade || undefined,
          })
      : null,
    [query, f.jurisdiction, f.subject, f.grade],
  )
  const codeHits = useApi(
    query && looksLikeCode(query) ? () => findStandard(query, f.jurisdiction || undefined) : null,
    [query, f.jurisdiction],
  )

  const rows = [...(codeHits.data?.standards ?? []), ...(results.data?.results ?? [])]
  const { cursor, onKeyDown } = useCursor(rows.length, (i) => navigate(standardHref(rows[i].id)))
  const codeCount = codeHits.data?.standards.length ?? 0

  const jurisdictions = Object.keys(st.data?.jurisdictions ?? {}).sort((a, b) =>
    a === 'Multi-State' ? -1 : b === 'Multi-State' ? 1 : a.localeCompare(b),
  )
  const subjects = Object.keys(st.data?.subjects ?? {}).sort()
  const standardCount = st.data?.nodesByLabel['StandardsFrameworkItem']
  const active = (Object.entries(f) as [keyof Filters, string][]).filter(([, v]) => v)

  const set = (k: keyof Filters, v: string) => setF((prev) => ({ ...prev, [k]: v }))
  const submit = (e: FormEvent) => e.preventDefault()

  return (
    <>
      <PageHead
        eyebrow="Search"
        title="Find a standard."
        lede={
          <>
            {standardCount ? `${fmt(standardCount)} standards` : 'Standards'} across{' '}
            {jurisdictions.length > 1
              ? `${jurisdictions.length} jurisdictions`
              : 'every US jurisdiction'}{' '}
            — by topic, wording, or code. Results appear as you type.
          </>
        }
      />

      <form onSubmit={submit} role="search">
        <div className="searchfield searchfield-sm" style={{ maxWidth: 720 }}>
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="fractions, photosynthesis, 4.OA.A.3…"
            aria-label="Search standards"
            autoFocus
          />
          <button type="submit">Search</button>
        </div>

        <div className="filters filters-sticky">
          <select
            className="field"
            value={f.jurisdiction}
            onChange={(e) => set('jurisdiction', e.target.value)}
            aria-label="Jurisdiction"
          >
            <option value="">All jurisdictions</option>
            {jurisdictions.map((j) => (
              <option key={j}>{j}</option>
            ))}
          </select>
          <select
            className="field"
            value={f.subject}
            onChange={(e) => set('subject', e.target.value)}
            aria-label="Subject"
          >
            <option value="">All subjects</option>
            {subjects.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select
            className="field"
            value={f.grade}
            onChange={(e) => set('grade', e.target.value)}
            aria-label="Grade"
          >
            <option value="">All grades</option>
            {GRADES.map((g) => (
              <option key={g} value={g}>
                Grade {g}
              </option>
            ))}
          </select>

          {active.map(([k, v]) => (
            <button key={k} type="button" className="chip chip-on" onClick={() => set(k, '')}>
              {k === 'grade' ? `Grade ${v}` : v} <span className="chip-x">×</span>
            </button>
          ))}
          {active.length > 1 && (
            <button
              type="button"
              className="chip"
              onClick={() => setF({ jurisdiction: '', subject: '', grade: '' })}
            >
              Clear all
            </button>
          )}
          <span className="count" style={{ marginLeft: 'auto' }}>
            {results.data ? `${fmt(results.data.resultCount)} matches` : ''}
          </span>
        </div>
      </form>

      {!q && (
        <Empty title="Start typing.">
          <p style={{ margin: '6px 0 0' }}>
            Search the wording of a standard (<a href="#/search?q=fractions">fractions</a>,{' '}
            <a href="#/search?q=photosynthesis">photosynthesis</a>) or paste a code (
            <a href="#/search?q=4.OA.A.3">4.OA.A.3</a>). A code matches once per jurisdiction that
            adopted it, so expect a set rather than a single hit.
          </p>
        </Empty>
      )}

      {(results.loading || codeHits.loading) && <Loading label="Searching" />}
      {results.error && <ErrorBox message={results.error} />}

      {codeCount > 0 && (
        <section className="section-tight">
          <div className="section-head">
            <h2 className="label">Exact code matches</h2>
            <span className="count">{codeHits.data?.matchCount}</span>
          </div>
          <Note text={codeHits.data?.note} />
          {codeHits.data?.standards.map((s, i) => (
            <StandardEntry key={s.id} s={s} cursor={i === cursor} />
          ))}
        </section>
      )}

      {results.data && (
        <section className="section-tight">
          <div className="section-head">
            <h2 className="label">Matches in statements</h2>
            <span className="count">{fmt(results.data.resultCount)}</span>
          </div>
          {results.data.resultCount === 0 && codeCount === 0 && (
            <Empty title="Nothing matches that wording.">
              <p style={{ margin: '6px 0 0' }}>
                {f.jurisdiction && `No hits in ${f.jurisdiction}. `}Try fewer or broader words
                {active.length > 0 && ', or drop a filter'}
                {looksLikeCode(query)
                  ? '.'
                  : ', or search a standard code like 4.OA.A.3 instead.'}
              </p>
            </Empty>
          )}
          {results.data.results.map((s, i) => (
            <StandardEntry key={s.id} s={s} cursor={i + codeCount === cursor} />
          ))}
        </section>
      )}
    </>
  )
}
