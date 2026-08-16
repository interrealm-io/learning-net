import type { FormEvent } from 'react'
import { crosswalk, findStandard, stats, useApi } from '../api'
import { navigate } from '../router'
import { ErrorBox, Loading, Note, StandardEntry } from '../ui'

function onSubmit(e: FormEvent<HTMLFormElement>) {
  e.preventDefault()
  const f = new FormData(e.currentTarget)
  const qs = new URLSearchParams()
  const standard = String(f.get('standard') ?? '').trim()
  const to = String(f.get('to') ?? '').trim()
  if (!standard) return
  qs.set('standard', standard)
  if (to) qs.set('to', to)
  navigate(`/crosswalk?${qs}`)
}

export function CrosswalkPage({ params }: { params: URLSearchParams }) {
  const standard = params.get('standard') ?? ''
  const to = params.get('to') ?? ''

  const st = useApi(stats, [])
  const xw = useApi(standard ? () => crosswalk(standard, to || undefined) : null, [standard, to])
  // When the ref was a bare code, several jurisdictions share it; offer the
  // alternatives so "from" is always an explicit choice, never a silent pick.
  const sameCode = useApi(
    xw.data && xw.data.standard.id !== standard
      ? () => findStandard(xw.data!.standard.statementCode ?? standard)
      : null,
    [xw.data?.standard.id, standard],
  )

  const jurisdictions = Object.keys(st.data?.jurisdictions ?? {}).sort((a, b) =>
    a === 'Multi-State' ? -1 : b === 'Multi-State' ? 1 : a.localeCompare(b),
  )

  return (
    <>
      <h1 className="hero">Compare across states.</h1>
      <p className="hero-sub">
        States align to the Multi-State spine, never to each other — so a state-to-state
        comparison is a two-hop walk, and this page always says when it took one.
      </p>

      {/* Uncontrolled selects apply defaultValue only on mount, so the form
          remounts when the option list arrives, not just when params change. */}
      <form
        className="searchbar"
        key={`${params.toString()}|${jurisdictions.length}`}
        onSubmit={onSubmit}
      >
        <input
          name="standard"
          type="search"
          defaultValue={standard}
          placeholder="Standard code, e.g. 4.OA.A.3"
          aria-label="Standard to compare"
        />
        <select name="to" defaultValue={to} aria-label="Compare to jurisdiction">
          <option value="">Every jurisdiction</option>
          {jurisdictions.map((j) => (
            <option key={j}>{j}</option>
          ))}
        </select>
        <button className="button" type="submit">
          Compare
        </button>
      </form>

      {xw.loading && <Loading />}
      {xw.error && <ErrorBox message={xw.error} />}

      {sameCode.data && sameCode.data.matchCount > 1 && (
        <p className="from-chips">
          From:{' '}
          {sameCode.data.standards.map((s) => (
            <a
              key={s.id}
              className={s.id === xw.data?.standard.id ? 'chip chip-active' : 'chip'}
              href={`#/crosswalk?standard=${encodeURIComponent(s.id)}${to ? `&to=${encodeURIComponent(to)}` : ''}`}
              aria-current={s.id === xw.data?.standard.id ? 'true' : undefined}
            >
              {s.jurisdiction}
            </a>
          ))}
        </p>
      )}

      {xw.data && (
        <div className="xw-grid">
          <div>
            <div className="section-head">
              <h2>This standard</h2>
            </div>
            <StandardEntry s={xw.data.standard} />
          </div>
          <div
            className={xw.data.viaMultiStateHub ? 'connector connector-inferred' : 'connector'}
          >
            <span className="connector-line" aria-hidden="true" />
            <span className="connector-label">
              {xw.data.viaMultiStateHub ? 'via Multi-State spine' : 'direct alignment'}
            </span>
          </div>
          <div>
            <div className="section-head">
              <h2>{to ? `In ${to}` : 'Aligned standards'}</h2>
              <span className="count">{xw.data.alignmentCount}</span>
            </div>
            <Note text={xw.data.note} />
            {xw.data.alignedStandards.map((s) => (
              <StandardEntry key={s.id} s={s} />
            ))}
          </div>
        </div>
      )}
    </>
  )
}
