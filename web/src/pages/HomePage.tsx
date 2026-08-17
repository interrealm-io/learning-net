import { useState } from 'react'
import type { FormEvent } from 'react'
import { searchStandards, stats, useApi } from '../api'
import { useCursor, useDebounced } from '../hooks'
import { navigate, standardHref } from '../router'
import { CodeBlock, Eyebrow, ErrorBox, fmt, Loading, StandardEntry } from '../ui'

const EXAMPLES = ['fractions', 'photosynthesis', '4.OA.A.3', 'place value']

// What a person can actually do with this thing, in the order they are likely
// to want it. Every card is a link to a page that already works — no card here
// describes a capability the mirror does not have.
const VERBS = [
  {
    do: 'Search',
    href: '#/search',
    title: 'Every statement, every jurisdiction',
    body: 'Full-text search across every standard in the mirror, filtered by state, subject, and grade. Answers come from a file on this machine, so there is no rate limit and no network hop.',
  },
  {
    do: 'Crosswalk',
    href: '#/crosswalk?standard=4.OA.A.3&to=Texas',
    title: 'One state’s standard, in another state',
    body: 'California’s 4.OA.A.3 to its Texas equivalents. States align only to the Multi-State spine, so this is two hops — taken automatically, and labeled when it happens.',
  },
  {
    do: 'Progressions',
    href: '#/search?q=4.OA.A.3',
    title: 'What comes before, what comes next',
    body: 'Open any standard for its prerequisites and where it leads. The edges exist only on the Multi-State math spine; the mirror bridges out and back for you.',
  },
  {
    do: 'Coverage',
    href: '#/coverage',
    title: 'Where the data is thin',
    body: 'A map of every jurisdiction by how much of it is actually crosswalked, with the isolated ones marked. Knowing where the graph is empty is half of trusting it.',
  },
  {
    do: 'Connect an AI',
    href: '#/mcp',
    title: 'The same answers, over MCP',
    body: 'Point Claude or any MCP client at this mirror and it answers with real standard codes from the same eleven queries this site runs on. Copy-paste config, no API key.',
  },
  {
    do: 'Provenance',
    href: '#/status',
    title: 'Which release is answering',
    body: 'Every answer traces to a versioned upstream export, checksummed at build. The mirror will tell you how stale it is rather than quietly guessing.',
  },
]

const FACTS = [
  {
    n: '26',
    title: 'Codes are not unique',
    body: 'A code like 4.OA.A.3 matches 26 nodes — one per jurisdiction that adopted it, plus the Multi-State original. Every lookup by code is a set, and it is treated as one.',
  },
  {
    n: '757',
    title: 'Progressions live on the spine',
    body: 'All 757 prerequisite edges are authored on Multi-State Mathematics. Ask a state standard directly and the honest answer is empty — unless something bridges for you.',
  },
  {
    n: '0',
    title: 'States never link to states',
    body: 'There is no California-to-Texas edge in the data. That comparison exists only as a two-hop walk through the spine, which something has to know to take.',
  },
]

const QUICKSTART = `git clone https://github.com/interrealm-io/learning-net
cd learning-net && uv tool install .

learning-net init     # downloads the export, builds the mirror
learning-net web      # this site, on your hardware
learning-net serve    # the same queries, over MCP`

// Six states, one hub, and the two dashed hops a crosswalk actually takes.
function SpineFigure() {
  const spokes = [
    { x: 44, y: 30, label: 'NY' },
    { x: 26, y: 84, label: 'CA' },
    { x: 62, y: 138, label: 'FL' },
    { x: 262, y: 30, label: 'IL' },
    { x: 298, y: 84, label: 'TX' },
    { x: 240, y: 138, label: 'WA' },
  ]
  return (
    <svg
      className="spine-figure"
      viewBox="0 0 340 176"
      role="img"
      aria-label="Six states each linking to a central Multi-State hub; California reaches Texas in two dashed hops through it"
    >
      {spokes.map((s) => (
        <line key={s.label} x1={s.x} y1={s.y} x2={168} y2={84} className="spoke" />
      ))}
      <line x1={26} y1={84} x2={168} y2={84} className="spoke spoke-hot" />
      <line x1={168} y1={84} x2={298} y2={84} className="spoke spoke-hot" />
      {spokes.map((s) => (
        <g key={s.label}>
          <circle cx={s.x} cy={s.y} r={19} className="halo" />
          <circle cx={s.x} cy={s.y} r={13} className="node" />
          <text x={s.x} y={s.y + 3} className="node-label">
            {s.label}
          </text>
        </g>
      ))}
      <circle cx={168} cy={84} r={20} className="hub" />
      <text x={168} y={87} className="hub-label">
        SPINE
      </text>
      <text x={168} y={126} className="node-label">
        MULTI-STATE
      </text>
    </svg>
  )
}

export function HomePage() {
  const [q, setQ] = useState('')
  const query = useDebounced(q.trim())
  const st = useApi(stats, [])
  const results = useApi(
    query.length >= 2 ? () => searchStandards({ query }) : null,
    [query],
  )
  const hits = results.data?.results.slice(0, 6) ?? []
  const { cursor, onKeyDown } = useCursor(hits.length, (i) => navigate(standardHref(hits[i].id)))

  const d = st.data
  const standards = d?.nodesByLabel['StandardsFrameworkItem']
  const jurisdictions = d ? Object.keys(d.jurisdictions).length : undefined
  const edges = d ? Object.values(d.edgesByLabel).reduce((a, b) => a + b, 0) : undefined

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (q.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`)
  }

  return (
    <>
      <section className="band band-paper home-hero">
        <div className="band-inner split">
          <div className="split-main">
            <Eyebrow>
              Self-hosted mirror
              {d?.snapshot?.kgVersion ? ` · Learning Commons KG v${d.snapshot.kgVersion}` : ''} ·
              Open source
            </Eyebrow>
            <h1 className="display">Find a standard.</h1>
            <p className="lede">
              {standards ? fmt(standards) : '258,430'} standards across{' '}
              {jurisdictions ?? 52} jurisdictions — search by topic, wording, or code. Everything
              on this page is answered by a copy of the graph running on this machine.
            </p>

            <form className="home-search" onSubmit={submit} role="search">
              <div className="searchfield">
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
              <p className="home-examples">
                Try{' '}
                {EXAMPLES.map((ex, i) => (
                  <span key={ex}>
                    {i > 0 && ' · '}
                    <a
                      href={`#/search?q=${encodeURIComponent(ex)}`}
                      onClick={(e) => {
                        e.preventDefault()
                        setQ(ex)
                      }}
                    >
                      {ex}
                    </a>
                  </span>
                ))}
                {hits.length > 0 && (
                  <>
                    {' '}
                    · <span className="kbd">↑</span> <span className="kbd">↓</span> to move,{' '}
                    <span className="kbd">↵</span> to open
                  </>
                )}
              </p>
            </form>

            {query.length >= 2 && (
              <div className="home-results">
                {results.loading && <Loading label="Searching" />}
                {results.error && <ErrorBox message={results.error} />}
                {results.data && (
                  <>
                    <div className="home-results-head">
                      <span className="label">
                        {results.data.resultCount === 0
                          ? 'No matches'
                          : `Top ${hits.length} of ${fmt(results.data.resultCount)}`}
                      </span>
                      {results.data.resultCount > hits.length && (
                        <a href={`#/search?q=${encodeURIComponent(query)}`}>
                          See all results ↓
                        </a>
                      )}
                    </div>
                    {hits.map((s, i) => (
                      <StandardEntry key={s.id} s={s} cursor={i === cursor} />
                    ))}
                    {results.data.resultCount === 0 && (
                      <p className="quiet">
                        Nothing matches that wording. Try fewer words, or a standard code like{' '}
                        <a href="#/search?q=4.OA.A.3">4.OA.A.3</a>.
                      </p>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          <div className="split-side">
            <SpineFigure />
            <div style={{ marginTop: 22, borderTop: '1px solid var(--line)', paddingTop: 18 }}>
              <p className="eyebrow-bare" style={{ color: 'var(--spine)', margin: '0 0 6px' }}>
                Solid authored · Dashed inferred
              </p>
              <p className="motto" style={{ margin: 0, borderLeft: 0, paddingLeft: 0 }}>
                Commons is the collection. Net is the distribution.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="band">
        <div className="band-inner">
          <div className="tiles">
            <div className="tile">
              <b>{standards ? fmt(standards) : '—'}</b>
              <small>Standards</small>
            </div>
            <div className="tile">
              <b>{jurisdictions ?? '—'}</b>
              <small>Jurisdictions</small>
            </div>
            <div className="tile">
              <b>{edges ? fmt(edges) : '—'}</b>
              <small>Connections</small>
            </div>
            <div className="tile">
              <b>{d ? Object.keys(d.subjects).length : '—'}</b>
              <small>Subjects</small>
            </div>
            <div className="tile">
              <b>0</b>
              <small>API keys needed</small>
            </div>
          </div>
        </div>
      </section>

      <section className="band band-paper">
        <div className="band-inner">
          <Eyebrow>What you can do here</Eyebrow>
          <h2 className="h1" style={{ maxWidth: '20ch' }}>
            Six things this mirror does that the hosted graph will not.
          </h2>
          <div className="verbs" style={{ marginTop: 'var(--s-6)' }}>
            {VERBS.map((v) => (
              <a key={v.do} className="verb" href={v.href}>
                <span className="verb-do">{v.do} →</span>
                <h3>{v.title}</h3>
                <p>{v.body}</p>
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="band">
        <div className="band-inner">
          <Eyebrow>Why the answers are different</Eyebrow>
          <h2 className="h1" style={{ maxWidth: '22ch' }}>
            The graph has a shape, and it decides whether a query returns anything.
          </h2>
          <p className="prose">
            Ask the hosted graph for the prerequisites of California’s{' '}
            <span className="code-chip">4.OA.A.3</span> and you get an empty list. Not an error — an
            empty list. Three facts explain it, and Learning Net encodes all three.
          </p>
          <div className="grid grid-3" style={{ marginTop: 'var(--s-6)' }}>
            {FACTS.map((f) => (
              <div key={f.title} className="card-ruled">
                <span className="verb-do">{f.n}</span>
                <h3 className="h3">{f.title}</h3>
                <p className="card-body">{f.body}</p>
              </div>
            ))}
          </div>
          <p className="prose" style={{ marginTop: 'var(--s-5)' }}>
            Because a tool that silently infers is worse than one that returns nothing, every answer
            that crossed the spine says so:{' '}
            <span className="spine-badge">inferred via Multi-State spine</span>. Solid means
            authored, dashed means inferred — on every page of this site and in every JSON response.{' '}
            <a href="#/docs">How to read the graph →</a>
          </p>
        </div>
      </section>

      <section className="band band-paper">
        <div className="band-inner split">
          <div className="split-main">
            <Eyebrow>Run your own</Eyebrow>
            <h2 className="h1" style={{ maxWidth: '18ch' }}>
              One command builds the mirror. It is yours after that.
            </h2>
            <p className="prose">
              The core is stdlib Python with zero dependencies, including the MCP server — a school
              IT admin with a stock Python install can run the whole thing. Upstream publishes the
              exports on a public CDN under CC BY-4.0, so there is no key, no account, and no
              request form.
            </p>
            <div className="cta-row">
              <a className="button" href="#/mcp">
                Connect an AI client
              </a>
              <a
                className="button button-quiet"
                href="https://github.com/interrealm-io/learning-net"
                rel="noreferrer"
              >
                Read the code ↗
              </a>
            </div>
          </div>
          <div className="split-side" style={{ flex: '1 1 420px' }}>
            <CodeBlock code={QUICKSTART} />
            <p className="quiet">
              No pip? A single-file zipapp runs the same commands:{' '}
              <span className="mono">python3 learning-net.pyz init</span>
            </p>
          </div>
        </div>
      </section>
    </>
  )
}
