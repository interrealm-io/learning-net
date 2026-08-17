import { stats, useApi } from '../api'
import { fmt, PageHead, Section } from '../ui'

export function AboutPage() {
  const st = useApi(stats, [])
  const d = st.data
  const standards = d?.nodesByLabel['StandardsFrameworkItem']

  return (
    <>
      <PageHead
        eyebrow="About"
        title="Commons is the collection. Net is the distribution."
        lede="Learning Net is a self-hosted mirror, MCP server, and explorer for the Learning Commons Knowledge Graph — an independent, open-source extension to the Learning Commons Platform."
      />

      <Section title="What it is">
        <p className="prose">
          Learning Commons aggregated something genuinely hard to assemble: the K-12 academic
          standards of {d ? Object.keys(d.jurisdictions).length : 52} US jurisdictions —{' '}
          {standards ? fmt(standards) : '258,430'} standards, the granular learning components
          beneath them, the alignments between them, and curriculum mapped onto them — then
          published the whole thing under CC BY-4.0 on a public CDN with no key, no account, and no
          gate. That is years of unglamorous work, and a licensing choice they did not have to make.
        </p>
        <p className="prose">
          Learning Net makes that graph something a school can run. Sync it, host it, query it,
          explore it, extend it. No network round-trip per lookup, no rate limit, no single point of
          failure, and no requirement that anyone else's server be up for a classroom to work. It
          mirrors the versioned exports, preserves every per-jurisdiction attribution verbatim, and
          always says which upstream release is answering.
        </p>
        <p className="pull">
          A mirror that cannot say how stale it is has no business being trusted — so this one says.
        </p>
      </Section>

      <Section title="Status">
        <p className="prose">
          Alpha. Upstream is in private beta and explicitly evolving with breaking changes, so sync
          reports schema drift rather than absorbing it. Breaking findings stop a sync and exit
          non-zero. <a href="#/docs">The docs</a> explain what the mirror will and will not infer on
          your behalf.
        </p>
      </Section>

      <Section title="Governance">
        <p className="prose">
          Learning Net is stewarded by the{' '}
          <a href="https://interrealm.org" rel="noreferrer">
            InterRealm Foundation
          </a>{' '}
          as non-profit open infrastructure for educational AI. It is not a commercial open-core
          product and there is no paid tier. What is and is not in scope — specifically what happens
          to a school's own curriculum if they put it in a mirror — is written down in{' '}
          <a
            href="https://github.com/interrealm-io/learning-net/blob/main/GOVERNANCE.md"
            rel="noreferrer"
          >
            GOVERNANCE.md
          </a>{' '}
          rather than left to trust.
        </p>
        <p className="prose">
          Code Apache-2.0. Data CC BY-4.0 by Learning Commons, attribution preserved on every node.
          Learning Net is an independent project, built in the spirit the license invites.
        </p>
      </Section>

      <div className="cta-row">
        <a className="button" href="#/">
          Search the graph
        </a>
        <a className="button button-quiet" href="#/mcp">
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
    </>
  )
}
