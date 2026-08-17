import type { ReactNode } from 'react'
import { PageHead } from '../ui'

const SECTIONS: { id: string; title: string; body: ReactNode }[] = [
  {
    id: 'reading',
    title: 'How to read an answer',
    body: (
      <>
        <p>
          Learning Net answers two kinds of question, and it never lets them look alike. An{' '}
          <strong>authored</strong> answer is a relationship somebody wrote into the data. An{' '}
          <strong>inferred</strong> answer is one this tool constructed by walking through the
          Multi-State spine because no direct edge exists.
        </p>
        <p>
          Inference is what makes cross-state questions answerable at all — but a tool that infers
          silently is worse than one that returns nothing. So the interface carries one rule
          everywhere: <strong>solid means authored, dashed means inferred</strong>, and brass is
          reserved for the spine and anything that crossed it. When you see{' '}
          <span className="spine-badge">inferred via Multi-State spine</span>, the mirror is telling
          you it did a two-hop walk on your behalf.
        </p>
        <p>
          The JSON says the same thing in the same place: results carry{' '}
          <span className="mono">bridgedViaMultiState</span> or{' '}
          <span className="mono">viaMultiStateHub</span>, and a{' '}
          <span className="mono">note</span> field explaining the hop in plain language. An AI client
          and a teacher looking at this screen get identical answers.
        </p>
      </>
    ),
  },
  {
    id: 'topology',
    title: 'Three facts about the graph',
    body: (
      <>
        <p>
          None of these are documented upstream, and all three decide whether a query returns
          anything. They are the reason this project exists.
        </p>
        <ul>
          <li>
            <strong>Standard codes are not unique.</strong> <span className="mono">4.OA.A.3</span>{' '}
            matches 26 nodes — one per jurisdiction that adopted the code, plus the Multi-State
            original. Every lookup by code is a set. Pass a jurisdiction when you mean a specific
            state, and treat a bare code as ambiguous until you do.
          </li>
          <li>
            <strong>Progressions live only on the Multi-State math spine.</strong> All 757
            prerequisite edges are authored there. No state standard carries one directly, and no
            ELA, Science, or Social Studies standard has one at all. Asking a California standard
            for its prerequisites returns an empty list — a true answer to the wrong question.
          </li>
          <li>
            <strong>Alignment is hub-and-spoke.</strong> States align to Multi-State, never to each
            other, so a California-to-Texas crosswalk is two hops. All 52,807 curriculum alignments
            likewise point only at Multi-State Mathematics.
          </li>
        </ul>
        <p>
          Learning Net encodes all three: it resolves a code to the whole set, hops out to the spine
          and back for progressions and curriculum, and walks both spokes for a crosswalk — then
          tells you it did.
        </p>
      </>
    ),
  },
  {
    id: 'coverage',
    title: 'Coverage: where the graph is thin',
    body: (
      <>
        <p>
          <a href="#/coverage">The coverage map</a> measures something nobody publishes, including
          upstream: how much of each jurisdiction is actually <em>connected</em>. A state can have
          thousands of standards and almost no crosswalk edges, which means claims of alignment to
          that state cannot be verified from this data at all.
        </p>
        <ul>
          <li>
            <strong>Crosswalked %</strong> — the share of a jurisdiction's standards that carry at
            least one alignment to the spine. This is the number that decides whether cross-state
            questions work for that state.
          </li>
          <li>
            <strong>Isolated</strong> — a jurisdiction with zero alignments. Marked in red with a
            glyph rather than a darker shade, because it is a status, not the bottom of a scale.
          </li>
          <li>
            <strong>Components / curriculum / progressions</strong> — how many standards carry
            teachable skills, aligned lessons, or prerequisite edges beneath them.
          </li>
        </ul>
        <p>
          Use <span className="mono">verify_alignment_claim</span> when a vendor says material is
          "aligned to 4.OA.A.3" for a state: it answers whether that code names anything real there,
          and hands back the local equivalents to ask them to restate against.
        </p>
      </>
    ),
  },
  {
    id: 'queries',
    title: 'The eleven queries',
    body: (
      <>
        <p>
          Everything in this explorer is one of eleven queries, and every one of them is also an MCP
          tool and an HTTP endpoint at <span className="mono">/api/&lt;tool&gt;</span>. The handler
          table is shared, so the web UI and an AI client cannot disagree.
        </p>
        <p>
          <a href="#/mcp">The MCP page</a> lists all eleven with their parameters and a live example
          for each.
        </p>
      </>
    ),
  },
  {
    id: 'provenance',
    title: 'Provenance and drift',
    body: (
      <>
        <p>
          Every mirror records the upstream release it was built from, the SHA-256 of both export
          files, and the builder version — visible on <a href="#/status">the status page</a> and in{' '}
          <span className="mono">graph_stats</span>. A mirror that cannot say how stale it is has no
          business being trusted.
        </p>
        <p>
          Upstream is in private beta and evolving with breaking changes. A mirror that silently
          absorbs a schema change is worse than no mirror, so{' '}
          <span className="mono">learning-net sync</span> diffs the structure of a new export
          against the live one — labels, edge types, triple patterns, property coverage — and
          classifies what moved. Breaking findings stop the sync and exit non-zero; use{' '}
          <span className="mono">--check</span> in CI to be told before a classroom is.
        </p>
      </>
    ),
  },
  {
    id: 'federation',
    title: 'Why two mirrors agree',
    body: (
      <>
        <p>
          Every node id in the published graph is a UUID v5 — derived by hash from stable inputs,
          never randomly assigned. Two independently built mirrors of the same source produce
          byte-identical ids.
        </p>
        <p>
          That is the whole basis for federation, and it is already true: a district can add its own
          curriculum against the shared spine and the additions merge without an id reconciliation
          layer. Local extension lands in a separate table so a sync never clobbers it.
        </p>
      </>
    ),
  },
  {
    id: 'licensing',
    title: 'Licensing and attribution',
    body: (
      <>
        <p>
          The code is Apache-2.0. The data is Learning Commons' work, published under CC BY-4.0, and
          every node and edge carries its own license plus a per-jurisdiction attribution statement
          naming the source department. Learning Net preserves both verbatim and surfaces them in
          every export path.
        </p>
        <p>
          Redistribution with attribution is what CC BY-4.0 grants; this project exercises exactly
          that and nothing more. Upstream's authenticated API is a separate surface governed by
          whatever agreement you have with them — Learning Net does not touch it.
        </p>
      </>
    ),
  },
]

export function DocsPage() {
  return (
    <>
      <PageHead
        eyebrow="Documentation"
        title="How to read this graph."
        lede="Enough to trust an answer: what is authored versus inferred, the three structural facts that decide whether a query returns anything, and how to check how stale this mirror is."
      />

      <div className="doc-layout">
        <nav className="doc-nav" aria-label="On this page">
          <ol>
            {SECTIONS.map((s) => (
              <li key={s.id}>
                <a
                  href="#/docs"
                  onClick={(e) => {
                    // Hash routing owns the fragment, so an in-page anchor has
                    // to scroll by hand rather than by href.
                    e.preventDefault()
                    document.getElementById(s.id)?.scrollIntoView({ behavior: 'smooth' })
                  }}
                >
                  {s.title}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <div>
          {SECTIONS.map((s) => (
            <section key={s.id} id={s.id} className="doc-section">
              <h2 className="h2">{s.title}</h2>
              {s.body}
            </section>
          ))}

          <p className="quiet">
            Longer-form documentation lives in the repository:{' '}
            <a href="https://github.com/interrealm-io/learning-net/blob/main/ARCHITECTURE.md" rel="noreferrer">
              ARCHITECTURE.md
            </a>
            ,{' '}
            <a href="https://github.com/interrealm-io/learning-net/blob/main/docs/federation.md" rel="noreferrer">
              federation.md
            </a>
            ,{' '}
            <a href="https://github.com/interrealm-io/learning-net/blob/main/DATA-LICENSE.md" rel="noreferrer">
              DATA-LICENSE.md
            </a>
            , and{' '}
            <a href="https://github.com/interrealm-io/learning-net/blob/main/GOVERNANCE.md" rel="noreferrer">
              GOVERNANCE.md
            </a>
            .
          </p>
        </div>
      </div>
    </>
  )
}
