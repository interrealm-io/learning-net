import { useState } from 'react'
import { coverageReport, stats, useApi } from '../api'
import { ErrorBox, fmt, Loading, Section, PageHead } from '../ui'
import type { CoverageRow } from '../types'

// A tile-grid map: each state is a same-sized tile in its rough geographic
// position. Deliberately not real geometry — equal tiles mean color is compared
// fairly (a choropleth of real shapes lets Alaska shout and D.C. vanish), and
// the layout is ~50 lines of data instead of a geometry dependency.
const GRID: Record<string, [abbr: string, col: number, row: number]> = {
  Alaska: ['AK', 0, 0],
  Maine: ['ME', 10, 0],
  Wisconsin: ['WI', 5, 1],
  Vermont: ['VT', 9, 1],
  'New Hampshire': ['NH', 10, 1],
  Washington: ['WA', 0, 2],
  Idaho: ['ID', 1, 2],
  Montana: ['MT', 2, 2],
  'North Dakota': ['ND', 3, 2],
  Minnesota: ['MN', 4, 2],
  Illinois: ['IL', 5, 2],
  Michigan: ['MI', 6, 2],
  'New York': ['NY', 8, 2],
  Massachusetts: ['MA', 9, 2],
  'Rhode Island': ['RI', 10, 2],
  Oregon: ['OR', 0, 3],
  Nevada: ['NV', 1, 3],
  Wyoming: ['WY', 2, 3],
  'South Dakota': ['SD', 3, 3],
  Iowa: ['IA', 4, 3],
  Indiana: ['IN', 5, 3],
  Ohio: ['OH', 6, 3],
  Pennsylvania: ['PA', 7, 3],
  'New Jersey': ['NJ', 8, 3],
  Connecticut: ['CT', 9, 3],
  California: ['CA', 0, 4],
  Utah: ['UT', 1, 4],
  Colorado: ['CO', 2, 4],
  Nebraska: ['NE', 3, 4],
  Missouri: ['MO', 4, 4],
  Kentucky: ['KY', 5, 4],
  'West Virginia': ['WV', 6, 4],
  Virginia: ['VA', 7, 4],
  Maryland: ['MD', 8, 4],
  Delaware: ['DE', 9, 4],
  Arizona: ['AZ', 1, 5],
  'New Mexico': ['NM', 2, 5],
  Kansas: ['KS', 3, 5],
  Arkansas: ['AR', 4, 5],
  Tennessee: ['TN', 5, 5],
  'North Carolina': ['NC', 6, 5],
  'South Carolina': ['SC', 7, 5],
  'Washington, D.C.': ['DC', 8, 5],
  Oklahoma: ['OK', 2, 6],
  Louisiana: ['LA', 3, 6],
  Mississippi: ['MS', 4, 6],
  Alabama: ['AL', 5, 6],
  Georgia: ['GA', 6, 6],
  Hawaii: ['HI', 0, 7],
  Texas: ['TX', 2, 7],
  Florida: ['FL', 7, 7],
}

// Sequential ramp: one hue (the app's green), light→dark, validated for
// monotone lightness, step gaps, and a 2:1 light end on the card surface.
// Isolated is NOT the bottom of this scale — it is a different condition
// (no alignment edges in either direction), so it wears the error color
// plus a "!" marker and never relies on hue alone.
const BINS = [
  { min: 15, cls: 'cov-b4', label: '15%+' },
  { min: 10, cls: 'cov-b3', label: '10–15%' },
  { min: 5, cls: 'cov-b2', label: '5–10%' },
  { min: -1, cls: 'cov-b1', label: 'under 5%' },
]

function binClass(r: CoverageRow): string {
  if (r.isolated) return 'cov-iso'
  return BINS.find((b) => r.crosswalkPct >= b.min)!.cls
}

interface Hover {
  row: CoverageRow
  x: number
  y: number
}

function Tooltip({ hover }: { hover: Hover }) {
  const r = hover.row
  return (
    <div className="cov-tooltip" style={{ left: hover.x, top: hover.y }} role="status">
      <b>{r.jurisdiction}</b>
      {r.isolated && <span className="cov-tooltip-iso">! no alignment edges</span>}
      <table>
        <tbody>
          <tr>
            <td>standards</td>
            <td>{fmt(r.standards)}</td>
          </tr>
          <tr>
            <td>crosswalked</td>
            <td>
              {fmt(r.crosswalked)} ({r.crosswalkPct}%)
            </td>
          </tr>
          <tr>
            <td>components</td>
            <td>
              {fmt(r.withComponents)} ({r.componentsPct}%)
            </td>
          </tr>
          <tr>
            <td>curriculum</td>
            <td>{fmt(r.withCurriculum)}</td>
          </tr>
          <tr>
            <td>progression</td>
            <td>{fmt(r.withProgression)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function TileMap({ rows }: { rows: CoverageRow[] }) {
  const [hover, setHover] = useState<Hover | null>(null)
  const byName = new Map(rows.map((r) => [r.jurisdiction, r]))
  const show = (name: string) => (e: React.MouseEvent | React.FocusEvent) => {
    const r = byName.get(name)
    if (!r) return
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    setHover({ row: r, x: rect.left + rect.width / 2, y: rect.top })
  }
  return (
    <div className="cov-map-wrap" onMouseLeave={() => setHover(null)}>
      <div className="cov-map" role="img" aria-label="US map of alignment coverage by state">
        {Object.entries(GRID).map(([name, [abbr, col, row]]) => {
          const r = byName.get(name)
          return (
            <button
              key={abbr}
              type="button"
              className={`cov-tile ${r ? binClass(r) : 'cov-none'}`}
              style={{ gridColumn: col + 1, gridRow: row + 1 }}
              aria-label={
                r
                  ? `${name}: ${r.crosswalkPct}% of ${fmt(r.standards)} standards crosswalked` +
                    (r.isolated ? ' — no alignment edges at all' : '')
                  : `${name}: no standards in this subject`
              }
              onMouseEnter={show(name)}
              onFocus={show(name)}
              onBlur={() => setHover(null)}
            >
              {abbr}
              {r?.isolated && <span aria-hidden="true">!</span>}
            </button>
          )
        })}
      </div>
      {hover && <Tooltip hover={hover} />}
    </div>
  )
}

function Legend() {
  return (
    <div className="cov-legend">
      <span className="cov-legend-title">standards with any cross-jurisdiction alignment</span>
      {[...BINS].reverse().map((b) => (
        <span key={b.cls} className="cov-legend-item">
          <i className={`cov-swatch ${b.cls}`} /> {b.label}
        </span>
      ))}
      <span className="cov-legend-item">
        <i className="cov-swatch cov-iso" aria-hidden="true">
          !
        </i>{' '}
        no alignment edges at all
      </span>
    </div>
  )
}

export function CoveragePage() {
  const [subject, setSubject] = useState('')
  const st = useApi(stats, [])
  const cov = useApi(() => coverageReport(subject || undefined), [subject])

  if (cov.error) return <ErrorBox message={cov.error} />
  const d = cov.data
  const nat = d?.national
  const spine = d?.byJurisdiction.find((r) => r.jurisdiction === 'Multi-State')
  const states = d?.byJurisdiction.filter((r) => r.jurisdiction !== 'Multi-State') ?? []

  return (
    <>
      <PageHead
        eyebrow="Coverage"
        title="The gap map."
        lede={
          <>
            "Standards-aligned" is only checkable where alignment edges exist. This page measures
            that layer for every jurisdiction — a measurement nobody else publishes, including
            upstream. It is not a criticism of the standards, which are complete; it is a work list
            for the connective tissue between them.
          </>
        }
      />

      {nat && (
        <div className="tiles">
          <div className="tile">
            <b>{fmt(nat.standards)}</b>
            <small>Standards</small>
          </div>
          <div className="tile">
            <b>{nat.crosswalkPct}%</b>
            <small>Carry any alignment</small>
          </div>
          <div className="tile">
            <b>{nat.jurisdictionsWithNoCrosswalk}</b>
            <small>Jurisdictions with none</small>
          </div>
          <div className="tile">
            <b>{fmt(nat.standardsInIsolatedJurisdictions)}</b>
            <small>Standards unverifiable</small>
          </div>
        </div>
      )}

      <div className="cov-filter">
        <label>
          Subject{' '}
          <select className="field" value={subject} onChange={(e) => setSubject(e.target.value)}>
            <option value="">All subjects</option>
            {Object.keys(st.data?.subjects ?? {})
              .sort()
              .map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
          </select>
        </label>
      </div>

      {cov.loading && <Loading />}

      {d && (
        <>
          <Section title="Alignment coverage by state">
            <Legend />
            <TileMap rows={states} />
          </Section>

          {spine && (
            <aside className="cov-spine">
              <span className="tag tag-spine">Multi-State</span> is the hub every state aligns
              through, not a place on the map. It holds all {fmt(spine.withCurriculum)} standards
              with aligned curriculum and all {fmt(spine.withProgression)} with a progression —
              every state reaches those only by bridging, and only where an alignment edge
              exists.
            </aside>
          )}

          <Section title="Worst first, per jurisdiction">
            <div className="table-wrap">
              <table className="table cov-table">
                <thead>
                  <tr>
                    <th scope="col">Jurisdiction</th>
                    <th scope="col">Standards</th>
                    <th scope="col">Crosswalk</th>
                    <th scope="col">Components</th>
                    <th scope="col">Curriculum</th>
                    <th scope="col">Progression</th>
                  </tr>
                </thead>
                <tbody>
                  {d.byJurisdiction.map((r) => (
                    <tr key={r.jurisdiction} className={r.isolated ? 'cov-row-iso' : undefined}>
                      <td>
                        {r.jurisdiction === 'Multi-State' ? (
                          <span className="tag tag-spine">Multi-State</span>
                        ) : (
                          r.jurisdiction
                        )}
                        {r.isolated && <span className="cov-iso-mark"> ! no alignment edges</span>}
                      </td>
                      <td className="num">{fmt(r.standards)}</td>
                      <td className="num">{r.crosswalkPct.toFixed(1)}%</td>
                      <td className="num">{r.componentsPct.toFixed(1)}%</td>
                      <td className="num">{fmt(r.withCurriculum)}</td>
                      <td className="num">{fmt(r.withProgression)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <p className="note">
            Absence of an alignment edge is not proof two standards are unrelated — only that no
            published alignment exists to check against. This measures the alignment layer, not
            the standards themselves.
          </p>
        </>
      )}
    </>
  )
}
