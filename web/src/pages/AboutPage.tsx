import { stats, useApi } from '../api'
import { fmt } from '../ui'

// The hub-and-spoke figure: states never link to each other, only to the
// Multi-State spine — so a state-to-state answer is two dashed hops.
function SpineFigure() {
  const spokes = [
    { x: 40, y: 28, label: 'NY' },
    { x: 24, y: 74, label: 'CA' },
    { x: 60, y: 120, label: 'FL' },
    { x: 260, y: 28, label: 'IL' },
    { x: 296, y: 74, label: 'TX' },
    { x: 240, y: 120, label: 'WA' },
  ]
  return (
    <svg className="spine-figure" viewBox="0 0 320 148" role="img"
      aria-label="Six states each linking to a central Multi-State hub; California reaches Texas in two hops through it">
      {spokes.map((s) => (
        <line key={s.label} x1={s.x} y1={s.y} x2={160} y2={74} className="spoke" />
      ))}
      <line x1={24} y1={74} x2={160} y2={74} className="spoke spoke-hot" />
      <line x1={160} y1={74} x2={296} y2={74} className="spoke spoke-hot" />
      {spokes.map((s) => (
        <g key={s.label}>
          <circle cx={s.x} cy={s.y} r={7} className="node" />
          <text x={s.x} y={s.y + 3.5} className="node-label">{s.label}</text>
        </g>
      ))}
      <circle cx={160} cy={74} r={13} className="hub" />
      <text x={160} y={100} className="hub-label">Multi-State spine</text>
    </svg>
  )
}

const FACTS = [
  {
    title: 'Codes are not unique',
    body: 'A code like 4.OA.A.3 matches 26 different nodes — one per jurisdiction that adopted it, plus the Multi-State original. Every lookup by code is a set, and Learning Net treats it as one.',
  },
  {
    title: 'Progressions live only on the spine',
    body: 'All 757 prerequisite edges are authored on Multi-State Mathematics. Ask a state standard for its prerequisites directly and the true answer is empty — unless something bridges for you.',
  },
  {
    title: 'States never link to states',
    body: 'Alignment is hub-and-spoke through the Multi-State spine. A California-to-Texas crosswalk does not exist as an edge; it exists as a two-hop walk that something has to know to take.',
  },
]

const UNLOCKS = [
  {
    href: '#/search?q=fractions',
    title: 'A classroom that works offline',
    body: 'The whole graph is a file on your hardware. No rate limit, no network round-trip, no dependence on anyone else’s server being up during first period.',
  },
  {
    href: '#/crosswalk?standard=4.OA.A.3&to=Texas',
    title: 'A crosswalk for a moving family',
    body: 'California’s 4.OA.A.3 to its Texas equivalents in one query — the two-hop walk through the spine, taken automatically and labeled honestly. Try it live.',
  },
  {
    title: 'An AI that cites the real standard',
    body: 'The MCP server speaks the same nine queries this site runs on, from the same mirror. An AI client and a teacher looking at this screen get identical answers.',
  },
  {
    href: '#/status',
    title: 'A mirror that admits how stale it is',
    body: 'Every answer traces to a versioned upstream release, checksummed at build. Sync detects structural drift and refuses to absorb it silently.',
  },
  {
    title: 'A district that extends the graph',
    body: 'Node identity is content-derived (UUID v5): two independent mirrors of the same source agree byte-for-byte, so local curriculum can merge against the shared spine. That is federation, already latent in the data.',
  },
]

export function AboutPage() {
  const st = useApi(stats, [])
  const d = st.data
  const standards = d?.nodesByLabel['StandardsFrameworkItem']

  return (
    <div className="about">
      <h1 className="hero hero-xl">
        Every standard.
        <br />
        Every state.
        <br />
        <em>One search.</em>
      </h1>
      <p className="hero-sub about-lede">
        Learning Net is a self-hosted mirror of the{' '}
        <a href="https://www.learningcommons.org" rel="noreferrer">Learning Commons</a> Knowledge
        Graph: the K-12 academic standards of every US jurisdiction, the teachable skills beneath
        them, and the curriculum aligned to them — running on your hardware, answering in
        milliseconds, working without the internet.
      </p>

      {d && (
        <div className="tiles">
          <div className="tile"><b>{fmt(standards ?? 0)}</b><small>Standards</small></div>
          <div className="tile"><b>{fmt(Object.keys(d.jurisdictions).length)}</b><small>Jurisdictions</small></div>
          <div className="tile"><b>{fmt(Object.values(d.edgesByLabel).reduce((a, b) => a + b, 0))}</b><small>Connections</small></div>
          <div className="tile"><b>{fmt(Object.keys(d.subjects).length)}</b><small>Subjects</small></div>
        </div>
      )}

      <section className="section">
        <div className="section-head"><h2>Built on Learning Commons</h2></div>
        <p className="about-body">
          Learning Commons did something genuinely hard: aggregated, normalized, and openly
          licensed the academic standards of 52 US jurisdictions — years of unglamorous work,
          published under CC BY-4.0 on a public CDN with no key, no account, and no gate. That
          choice is what makes a project like this possible, and Learning Net exercises exactly
          the freedom it grants: mirror the versioned exports, preserve every per-jurisdiction
          attribution verbatim, and always say which upstream release is answering.
        </p>
        <p className="about-motto">Commons is the collection. Net is the distribution.</p>
      </section>

      <section className="section">
        <div className="section-head"><h2>Why cross-search is hard — and why this one works</h2></div>
        <p className="about-body">
          Ask the hosted graph for the prerequisites of California&rsquo;s <span className="code-chip">4.OA.A.3</span>{' '}
          and you get an empty list. Not an error — an empty list. The standard is real, the data
          is real, and the answer is still empty, because the graph has a shape nobody documents:
        </p>
        <SpineFigure />
        <div className="fact-grid">
          {FACTS.map((f) => (
            <div key={f.title} className="fact-card">
              <h3>{f.title}</h3>
              <p>{f.body}</p>
            </div>
          ))}
        </div>
        <p className="about-body">
          Learning Net encodes all three facts and bridges automatically — one search that spans
          every jurisdiction and comes back with the answer. And because a tool that silently
          infers is worse than one that returns nothing, every answer that crossed the spine
          wears its badge: <span className="spine-badge">inferred via Multi-State spine</span>{' '}
          — solid means authored, dashed means inferred, everywhere in this interface.
        </p>
      </section>

      <section className="section">
        <div className="section-head"><h2>What that unlocks</h2></div>
        <div className="possible-grid">
          {UNLOCKS.map((u) =>
            u.href ? (
              <a key={u.title} className="possible-card" href={u.href}>
                <h3>{u.title}</h3>
                <p>{u.body}</p>
              </a>
            ) : (
              <div key={u.title} className="possible-card">
                <h3>{u.title}</h3>
                <p>{u.body}</p>
              </div>
            ),
          )}
        </div>
      </section>

      <div className="about-cta">
        <a className="button" href="#/search">Search the graph</a>
        <a className="button button-quiet" href="#/crosswalk?standard=4.OA.A.3&to=Texas">
          Try the crosswalk
        </a>
        <a className="button button-quiet" href="https://github.com/interrealm-io/learning-net" rel="noreferrer">
          Read the code
        </a>
      </div>

      <p className="quiet about-fine">
        Code Apache-2.0, stewarded by the InterRealm Foundation as non-profit open infrastructure.
        Data CC BY-4.0 by Learning Commons, attribution preserved on every node. Learning Net is
        an independent project, built in the spirit the license invites.
      </p>
    </div>
  )
}
