import type { FormEvent } from 'react'
import { crosswalk, findStandard, stats, useApi } from '../api'
import { navigate } from '../router'
import { ErrorBox, Loading, Note, PageHead, StandardEntry } from '../ui'

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
      <PageHead
        eyebrow="Crosswalk"
        title="Compare across states."
        lede="States align to the Multi-State spine, never to each other — so a state-to-state comparison is a two-hop walk, and this page always says when it took one."
      />

      <form className="row" key={params.toString()} onSubmit={onSubmit}>
        <div className="searchfield searchfield-sm" style={{ flex: '1 1 300px', maxWidth: 460 }}>
          <input
            name="standard"
            type="search"
            defaultValue={standard}
            placeholder="Standard code, e.g. 4.OA.A.3"
            aria-label="Standard to compare"
          />
          <button type="submit">Compare</button>
        </div>
        {/* Keyed by option count: remounts when stats arrive so defaultValue
            applies, without remounting the form and wiping typed input. */}
        <select
          className="field"
          name="to"
          key={jurisdictions.length}
          defaultValue={to}
          aria-label="Compare to jurisdiction"
        >
          <option value="">Every jurisdiction</option>
          {jurisdictions.map((j) => (
            <option key={j}>{j}</option>
          ))}
        </select>
      </form>

      {xw.loading && <Loading />}
      {xw.error && <ErrorBox message={xw.error} />}

      {sameCode.data && sameCode.data.matchCount > 1 && (
        <p className="chips" style={{ marginTop: 'var(--s-4)' }}>
          <span className="label">From</span>
          {sameCode.data.standards.map((s) => (
            <a
              key={s.id}
              className={s.id === xw.data?.standard.id ? 'chip chip-on' : 'chip'}
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
              <h2 className="label">This standard</h2>
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
              <h2 className="label">{to ? `In ${to}` : 'Aligned standards'}</h2>
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
