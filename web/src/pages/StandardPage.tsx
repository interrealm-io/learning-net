import { context, curriculum, learningComponents, progression, useApi } from '../api'
import { standardHref } from '../router'
import { ErrorBox, grades, Loading, Note, Section, SpineBadge, StandardEntry, Tags } from '../ui'
import type { Fetched } from '../api'
import type { ProgressionResult } from '../types'

function ProgressionList({ title, p }: { title: string; p: Fetched<ProgressionResult> }) {
  return (
    <Section title={title} aside={<SpineBadge on={p.data?.bridgedViaMultiState} />}>
      {p.loading && <Loading />}
      {p.error && <ErrorBox message={p.error} />}
      <Note text={p.data?.note} />
      {p.data?.progression.map((entry) => (
        <div key={entry.id} className="entry-group">
          <StandardEntry s={entry} />
          {entry.equivalentInJurisdiction?.map((eq) => (
            <a key={eq.id} className="equiv" href={standardHref(eq.id)}>
              same standard in {eq.jurisdiction}: {eq.statementCode ?? eq.id}
            </a>
          ))}
        </div>
      ))}
    </Section>
  )
}

export function StandardPage({ id }: { id: string }) {
  const ctx = useApi(() => context(id), [id])
  const comps = useApi(() => learningComponents(id), [id])
  const back = useApi(() => progression(id, 'backward'), [id])
  const fwd = useApi(() => progression(id, 'forward'), [id])
  const curr = useApi(() => curriculum(id), [id])

  if (ctx.loading) return <Loading />
  if (ctx.error) return <ErrorBox message={ctx.error} />
  const d = ctx.data!
  const s = d.standard

  return (
    <>
      <div className="detail-head">
        <Tags s={s} />
        {s.statement && <p className="statement statement-lg">{s.statement}</p>}
        <a className="button" href={`#/crosswalk?standard=${encodeURIComponent(s.id)}`}>
          Compare across states
        </a>
      </div>

      <div className="detail-cols">
        <div>
          <Section
            title="Learning components"
            aside={comps.data && <span className="count">{comps.data.componentCount}</span>}
          >
            {comps.loading && <Loading />}
            {comps.error && <ErrorBox message={comps.error} />}
            {comps.data?.componentCount === 0 && (
              <p className="quiet">No learning components are attached to this standard.</p>
            )}
            {comps.data?.learningComponents.map((c) => (
              <p key={c.id} className="statement component">
                {c.component}
              </p>
            ))}
          </Section>

          <ProgressionList title="Prerequisites" p={back} />
          <ProgressionList title="Leads to" p={fwd} />

          <Section
            title="Lessons & activities"
            aside={<SpineBadge on={curr.data?.bridgedViaMultiState} />}
          >
            {curr.loading && <Loading />}
            {curr.error && <ErrorBox message={curr.error} />}
            <Note text={curr.data?.note} />
            <div className="curriculum-grid">
              {curr.data?.curriculum.map((item) => (
                <div key={item.id} className="curriculum-card">
                  <span className="tag tag-quiet">{item.type}</span>
                  <p>{item.name ?? 'Untitled'}</p>
                  {item.gradeLevel && <span className="quiet">{grades(item.gradeLevel)}</span>}
                </div>
              ))}
            </div>
          </Section>
        </div>

        <aside className="detail-side">
          <h2>Where it sits</h2>
          <ol className="ladder">
            {[...d.ancestors].reverse().map((a) => (
              <li key={a.id}>
                <a href={standardHref(a.id)}>
                  {a.statementCode ?? a.statement ?? a.statementType ?? a.label}
                </a>
              </li>
            ))}
            <li aria-current="true">{s.statementCode ?? 'this standard'}</li>
          </ol>
          {d.childCount > 0 && (
            <>
              <h2>
                Children <span className="count">{d.childCount}</span>
              </h2>
              <ul className="child-list">
                {d.children.slice(0, 8).map((c) => (
                  <li key={c.id}>
                    <a href={standardHref(c.id)}>{c.statementCode ?? c.statement ?? c.id}</a>
                  </li>
                ))}
                {d.childCount > 8 && <li className="quiet">and {d.childCount - 8} more</li>}
              </ul>
            </>
          )}
        </aside>
      </div>
    </>
  )
}
