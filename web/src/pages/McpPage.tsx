import { CodeBlock, Eyebrow, PageHead, Section } from '../ui'

const CONFIG = `{
  "mcpServers": {
    "learning-net": {
      "command": "learning-net",
      "args": ["serve", "--db", "/srv/learning-net/data/kg.sqlite"]
    }
  }
}`

const CONFIG_PYZ = `{
  "mcpServers": {
    "learning-net": {
      "command": "python3",
      "args": ["/srv/learning-net.pyz", "serve", "--db", "/srv/learning-net/data/kg.sqlite"]
    }
  }
}`

const ASKS = [
  'What does 4.OA.A.3 say, and which states adopted that code?',
  'A vendor says this lesson is aligned to 4.OA.A.3 for Texas. Is that claim addressable?',
  'What should a student know before California’s 4.OA.A.3?',
  'Which jurisdictions have almost no crosswalk coverage in Science?',
]

const TOOLS: [name: string, params: string, answers: string, href?: string][] = [
  ['graph_stats', '—', 'Shape and provenance of this mirror: counts by label, coverage by jurisdiction and subject, which upstream release built it.', '#/status'],
  ['search_standards', 'query, jurisdiction?, subject?, gradeLevel?, limit?', 'Full-text search over every statement, ranked by BM25 — for when you do not know the code.', '#/search?q=fractions'],
  ['find_standard', 'statementCode, jurisdiction?, subject?, limit?', 'Resolve a code to its official statement. Returns a set: the same code is reused across jurisdictions, Multi-State first.', '#/search?q=4.OA.A.3'],
  ['crosswalk_standard', 'standard, toJurisdiction?, limit?', 'One jurisdiction’s standard to another’s. Two hops through the spine, taken automatically, flagged with viaMultiStateHub.', '#/crosswalk?standard=4.OA.A.3&to=Texas'],
  ['get_progression', 'standard, direction, limit?', 'Prerequisites or what a standard leads to. Bridged out to the Multi-State math spine and back, flagged with bridgedViaMultiState.'],
  ['get_learning_components', 'standard', 'The granular teachable skills beneath a standard.'],
  ['get_standard_context', 'standard, maxDepth?, childLimit?', 'Where a standard sits in its framework: ancestors up to the document, plus its children.'],
  ['find_curriculum', 'standard, kind?, limit?', 'Lessons and activities aligned to a standard. All 52,807 alignments point at Multi-State Mathematics, so state queries are bridged.'],
  ['verify_alignment_claim', 'statementCode, jurisdiction, subject?', 'Whether an "aligned to 4.OA.A.3" claim names anything real in a given state — with the local equivalents to ask a vendor to restate against.'],
  ['coverage_report', 'subject?', 'How much of each jurisdiction is actually connected, worst first. Nobody publishes this measurement, including upstream.', '#/coverage'],
  ['get_node', 'id', 'The raw node, every property, exactly as upstream published it.'],
]

export function McpPage() {
  return (
    <>
      <PageHead
        eyebrow="MCP server"
        title="The same answers, inside your AI client."
        lede="Learning Net speaks the Model Context Protocol over stdio. Point a client at the mirror and it answers from the same eleven queries this site runs on — same database file, same inference labels, no API key and no network."
      />

      <Section title="1 · Add it to your client">
        <p className="prose">
          Any MCP client works. This is the config shape most of them use — set{' '}
          <span className="mono">--db</span> to wherever{' '}
          <span className="mono">learning-net init</span> put the mirror.
        </p>
        <CodeBlock code={CONFIG} />
        <p className="quiet">
          Running the single-file zipapp instead of an installed package? Same thing, with the
          interpreter first:
        </p>
        <CodeBlock code={CONFIG_PYZ} />
        <p className="prose">
          Claude Desktop reads{' '}
          <span className="mono">~/Library/Application Support/Claude/claude_desktop_config.json</span>{' '}
          on macOS and <span className="mono">%APPDATA%\Claude\claude_desktop_config.json</span> on
          Windows. Restart the client after editing it.
        </p>
      </Section>

      <Section title="2 · Ask it something only a mirror can answer">
        <ul className="doc-section" style={{ paddingLeft: 'var(--s-5)' }}>
          {ASKS.map((a) => (
            <li key={a} style={{ fontFamily: 'var(--serif)', fontSize: 17, marginBottom: 8 }}>
              {a}
            </li>
          ))}
        </ul>
        <p className="prose">
          The answers arrive with real statement text and real codes, and every result that crossed
          the Multi-State spine carries{' '}
          <span className="mono">bridgedViaMultiState</span> or{' '}
          <span className="mono">viaMultiStateHub</span> — so a model can tell the client what the
          data says versus what the tool inferred, instead of blurring the two.
        </p>
      </Section>

      <Section title="The eleven queries">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Tool</th>
                <th scope="col">Parameters</th>
                <th scope="col">Answers</th>
              </tr>
            </thead>
            <tbody>
              {TOOLS.map(([name, params, answers, href]) => (
                <tr key={name} className="tool-row">
                  <td>{name}</td>
                  <td className="tool-params">{params}</td>
                  <td>
                    {answers}
                    {href && (
                      <>
                        {' '}
                        <a href={href}>Try it →</a>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="quiet" style={{ marginTop: 'var(--s-4)' }}>
          The web explorer calls these same handlers over HTTP at{' '}
          <span className="mono">/api/&lt;tool&gt;?param=value</span> — the table is imported, not
          reimplemented, so the two surfaces cannot drift apart.
        </p>
      </Section>

      <section className="band band-paper" style={{ marginTop: 'var(--s-8)', border: 0 }}>
        <div style={{ padding: 'var(--s-5) 0 0', borderTop: '1px solid var(--line-strong)' }}>
          <Eyebrow>No gate</Eyebrow>
          <p className="prose">
            There is no key to request, no quota to exhaust, and no vendor to stay in good standing
            with. The graph is a file; the server reads it. If the building loses internet during
            first period, every query on this page still answers.
          </p>
        </div>
      </section>
    </>
  )
}
