import type { FormEvent } from 'react'
import { findStandard, searchStandards, stats, useApi } from '../api'
import { navigate } from '../router'
import { ErrorBox, fmt, Loading, Note, StandardEntry } from '../ui'

const GRADES = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']

// A bare code like 4.OA.A.3 or HS-LS2-5 is one unspaced token with a digit and
// a separator; searching statements won't find it, so codes get a direct lookup.
const looksLikeCode = (q: string) => /^\S+$/.test(q) && /\d/.test(q) && /[.-]/.test(q)

function onSubmit(e: FormEvent<HTMLFormElement>) {
  e.preventDefault()
  const f = new FormData(e.currentTarget)
  const qs = new URLSearchParams()
  for (const k of ['q', 'jurisdiction', 'subject', 'grade']) {
    const v = String(f.get(k) ?? '').trim()
    if (v) qs.set(k, v)
  }
  navigate(`/?${qs}`)
}

export function SearchPage({ params }: { params: URLSearchParams }) {
  const q = params.get('q') ?? ''
  const jurisdiction = params.get('jurisdiction') ?? ''
  const subject = params.get('subject') ?? ''
  const grade = params.get('grade') ?? ''

  const st = useApi(stats, [])
  const results = useApi(
    q
      ? () =>
          searchStandards({
            query: q,
            jurisdiction: jurisdiction || undefined,
            subject: subject || undefined,
            gradeLevel: grade || undefined,
          })
      : null,
    [q, jurisdiction, subject, grade],
  )
  const codeHits = useApi(
    q && looksLikeCode(q) ? () => findStandard(q, jurisdiction || undefined) : null,
    [q, jurisdiction],
  )

  const jurisdictions = Object.keys(st.data?.jurisdictions ?? {}).sort((a, b) =>
    a === 'Multi-State' ? -1 : b === 'Multi-State' ? 1 : a.localeCompare(b),
  )
  const subjects = Object.keys(st.data?.subjects ?? {}).sort()
  const standardCount = st.data?.nodesByLabel['StandardsFrameworkItem']

  return (
    <>
      <h1 className="hero">Find a standard.</h1>
      <p className="hero-sub">
        {standardCount ? `${fmt(standardCount)} standards` : 'Standards'} across{' '}
        {jurisdictions.length > 1 ? `${jurisdictions.length} jurisdictions` : 'every US jurisdiction'}{' '}
        — search by topic, wording, or code.
      </p>

      <form className="searchbar" key={params.toString()} onSubmit={onSubmit}>
        <input
          name="q"
          type="search"
          defaultValue={q}
          placeholder="fractions, photosynthesis, 4.OA.A.3…"
          aria-label="Search standards"
          autoFocus
        />
        {/* Uncontrolled selects apply defaultValue only on mount; keying each
            select by its option count remounts it when stats arrive — without
            remounting the form, which would wipe in-progress typing. */}
        <select
          name="jurisdiction"
          key={jurisdictions.length}
          defaultValue={jurisdiction}
          aria-label="Jurisdiction"
        >
          <option value="">All jurisdictions</option>
          {jurisdictions.map((j) => (
            <option key={j}>{j}</option>
          ))}
        </select>
        <select name="subject" key={subjects.length} defaultValue={subject} aria-label="Subject">
          <option value="">All subjects</option>
          {subjects.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select name="grade" defaultValue={grade} aria-label="Grade">
          <option value="">All grades</option>
          {GRADES.map((g) => (
            <option key={g} value={g}>
              Grade {g}
            </option>
          ))}
        </select>
        <button className="button" type="submit">
          Search
        </button>
      </form>

      {!q && (
        <p className="examples">
          Try{' '}
          {['fractions', 'photosynthesis', '4.OA.A.3'].map((ex, i) => (
            <span key={ex}>
              {i > 0 && ' · '}
              <a href={`#/?q=${encodeURIComponent(ex)}`}>{ex}</a>
            </span>
          ))}
        </p>
      )}

      {codeHits.data && codeHits.data.matchCount > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>Code matches</h2>
            <span className="count">{codeHits.data.matchCount}</span>
          </div>
          <Note text={codeHits.data.note} />
          {codeHits.data.standards.map((s) => (
            <StandardEntry key={s.id} s={s} />
          ))}
        </section>
      )}

      {results.loading && <Loading />}
      {results.error && <ErrorBox message={results.error} />}
      {results.data && (
        <section className="section">
          <div className="section-head">
            <h2>Matches in statements</h2>
            <span className="count">{results.data.resultCount}</span>
          </div>
          {results.data.resultCount === 0 && (
            <p className="quiet">
              Nothing matches that wording{jurisdiction && ` in ${jurisdiction}`}. Try fewer or
              broader words{looksLikeCode(q) ? '' : ', or a standard code like 4.OA.A.3'}.
            </p>
          )}
          {results.data.results.map((s) => (
            <StandardEntry key={s.id} s={s} />
          ))}
        </section>
      )}
    </>
  )
}
