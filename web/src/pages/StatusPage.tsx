import { stats, useApi } from '../api'
import { ErrorBox, fmt, Loading, Section, PageHead } from '../ui'

function ago(iso?: string) {
  if (!iso) return null
  const days = Math.floor((Date.now() - Date.parse(iso)) / 86_400_000)
  if (Number.isNaN(days)) return null
  return days <= 0 ? 'today' : days === 1 ? 'yesterday' : `${days} days ago`
}

// A single-series bar list: identity is the row label, magnitude is the bar,
// and every value is directly labeled — no legend, no color coding needed.
function BarList({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  const max = entries[0]?.[1] ?? 1
  return (
    <Section title={title}>
      <div className="bars">
        {entries.map(([label, n]) => (
          <div key={label} className="bar-row" title={`${label}: ${fmt(n)}`}>
            <span className="bar-label">{label}</span>
            <span className="bar-track">
              <span className="bar" style={{ width: `${Math.max((n / max) * 100, 0.6)}%` }} />
            </span>
            <span className="bar-value">{fmt(n)}</span>
          </div>
        ))}
      </div>
    </Section>
  )
}

export function StatusPage() {
  const st = useApi(stats, [])
  if (st.loading) return <Loading />
  if (st.error) return <ErrorBox message={st.error} />
  const d = st.data!
  const snap = d.snapshot ?? {}
  const total = (m: Record<string, number>) => Object.values(m).reduce((a, b) => a + b, 0)

  return (
    <>
      <PageHead
        eyebrow="Status"
        title="This mirror."
        lede={
          snap.kgVersion ? (
            <>
              Built {ago(snap.builtAt) ?? snap.builtAt} from Learning Commons KG v{snap.kgVersion}.
              A mirror that cannot say how stale it is has no business being trusted.
            </>
          ) : (
            'Provenance is missing — this mirror predates provenance tracking; rebuild it.'
          )
        }
      />

      <div className="tiles">
        <div className="tile">
          <b>{fmt(total(d.nodesByLabel))}</b>
          <small>Nodes</small>
        </div>
        <div className="tile">
          <b>{fmt(total(d.edgesByLabel))}</b>
          <small>Edges</small>
        </div>
        <div className="tile">
          <b>{fmt(Object.keys(d.jurisdictions).length)}</b>
          <small>Jurisdictions</small>
        </div>
        <div className="tile">
          <b>{fmt(Object.keys(d.subjects).length)}</b>
          <small>Subjects</small>
        </div>
      </div>

      <Section title="Provenance">
        <dl className="provenance">
          {(
            [
              ['Upstream release', snap.kgVersion && `v${snap.kgVersion}`],
              ['Built', snap.builtAt],
              ['Source', snap.source],
              ['Builder', snap.builderVersion && `learning-net ${snap.builderVersion}`],
              ['nodes.jsonl SHA-256', snap.nodesSha256],
              ['relationships.jsonl SHA-256', snap.relationshipsSha256],
            ] as const
          ).map(
            ([label, value]) =>
              value && (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd className={label.includes('SHA') ? 'mono' : undefined} title={value}>
                    {label.includes('SHA') ? `${value.slice(0, 16)}…` : value}
                  </dd>
                </div>
              ),
          )}
        </dl>
      </Section>

      <BarList title="Nodes by label" data={d.nodesByLabel} />
      <BarList title="Edges by type" data={d.edgesByLabel} />

      <Section title={`Standards by jurisdiction`}>
        <details>
          <summary>All {Object.keys(d.jurisdictions).length} jurisdictions</summary>
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Jurisdiction</th>
                <th scope="col">Standards</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(d.jurisdictions)
                .sort((a, b) => b[1] - a[1])
                .map(([j, n]) => (
                  <tr key={j}>
                    <td>{j}</td>
                    <td className="num">{fmt(n)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </details>
      </Section>
    </>
  )
}
