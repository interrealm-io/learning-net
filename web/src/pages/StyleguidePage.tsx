import type { ReactNode } from 'react'
import { CodeBlock, Empty, ErrorBox, Loading, Note, PageHead, Section, SpineBadge } from '../ui'

const COLORS: [group: string, tokens: [name: string, use: string][]][] = [
  [
    'Surface',
    [
      ['--paper', 'app background'],
      ['--paper-2', 'text on dark'],
      ['--card', 'panels'],
      ['--wash', 'quiet fill'],
      ['--board', 'top bar, code'],
      ['--board-2', 'soft dark'],
    ],
  ],
  [
    'Ink',
    [
      ['--ink', 'primary text'],
      ['--ink-2', 'body prose'],
      ['--ink-3', 'secondary, labels'],
      ['--line', 'default rule'],
      ['--line-2', 'faint rule'],
    ],
  ],
  [
    'Action — interaction only, never decoration',
    [
      ['--action', 'links, primary button'],
      ['--action-deep', 'hover'],
      ['--action-wash', 'tint'],
    ],
  ],
  [
    'Spine — inference only, nothing else',
    [
      ['--spine', 'brass text'],
      ['--spine-line', 'dashed edges'],
      ['--spine-bg', 'brass fill'],
    ],
  ],
  [
    'Status and ramp',
    [
      ['--ok', 'bars, healthy'],
      ['--error', 'errors, isolated'],
      ['--ramp-1', 'coverage 1'],
      ['--ramp-2', 'coverage 2'],
      ['--ramp-3', 'coverage 3'],
      ['--ramp-4', 'coverage 4'],
    ],
  ],
]

const TYPE: [token: string, cls: string, sample: string][] = [
  ['--t-display / serif', 'display', 'Find a standard.'],
  ['--t-h1 / serif', 'h1', 'Compare across states.'],
  ['--t-h2 / serif', 'h2', 'Where the data is thin'],
  ['--t-lede / sans', 'lede', 'Standards across 52 jurisdictions — by topic, wording, or code.'],
  ['--t-prose / sans', 'prose', 'Body copy sits at 16.5px on a 1.7 line height and never runs wider than 68 characters.'],
  ['--t-body / serif', 'statement', 'Interpret a multiplication equation as a comparison.'],
  ['--t-small / sans', 'quiet', 'Secondary text, captions, and counts.'],
  ['--t-micro / mono', 'label', 'Section label'],
]

function Row({ token, children }: { token: string; children: ReactNode }) {
  return (
    <div className="sg-specimen">
      <code className="mono">{token}</code>
      <div className="sg-demo">{children}</div>
    </div>
  )
}

export function StyleguidePage() {
  return (
    <>
      <PageHead
        eyebrow="Style guide"
        title="One system, six files."
        lede="The foundation layer is InterRealm's — same paper, same ink, same action blue, same 2px corner, same three typefaces. The one thing Learning Net adds is a semantic rule: brass is the Multi-State spine, dashed is inference, and nothing else may use either."
      />

      <Section title="Color">
        {COLORS.map(([group, tokens]) => (
          <div key={group} style={{ marginBottom: 'var(--s-5)' }}>
            <p className="label" style={{ marginBottom: 'var(--s-2)' }}>
              {group}
            </p>
            <div className="sg-swatches">
              {tokens.map(([name, use]) => (
                <div key={name} className="sg-swatch">
                  <i style={{ background: `var(${name})` }} />
                  <span>
                    <b>{name}</b>
                    {use}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </Section>

      <Section title="Type">
        {TYPE.map(([token, cls, sample]) => (
          <div key={token} className="sg-specimen">
            <code className="mono">{token}</code>
            <div className={cls} style={{ margin: 0, maxWidth: '100%' }}>
              {sample}
            </div>
          </div>
        ))}
      </Section>

      <Section title="Components">
        <Row token=".button">
          <a className="button" href="#/styleguide">
            Primary
          </a>
          <a className="button button-quiet" href="#/styleguide">
            Quiet
          </a>
          <button className="button button-small" type="button">
            Small
          </button>
          <button className="button" type="button" disabled>
            Disabled
          </button>
        </Row>

        <Row token=".searchfield">
          <div className="searchfield searchfield-sm" style={{ minWidth: 320 }}>
            <input type="search" placeholder="fractions, 4.OA.A.3…" aria-label="Demo search" />
            <button type="button">Search</button>
          </div>
          <select className="field" aria-label="Demo select" defaultValue="">
            <option value="">All jurisdictions</option>
          </select>
        </Row>

        <Row token=".chip">
          <span className="chip">Filter</span>
          <span className="chip chip-on">
            California <span className="chip-x">×</span>
          </span>
          <span className="kbd">↵</span>
        </Row>

        <Row token=".tag / .code-chip">
          <span className="code-chip">4.OA.A.3</span>
          <span className="tag">California</span>
          <span className="tag tag-spine">Multi-State</span>
          <span className="tag tag-quiet">Mathematics</span>
        </Row>

        <Row token=".spine-badge">
          <SpineBadge on />
        </Row>

        <Row token=".tile">
          <div className="tiles" style={{ minWidth: 320 }}>
            <div className="tile">
              <b>258,430</b>
              <small>Standards</small>
            </div>
            <div className="tile">
              <b>52</b>
              <small>Jurisdictions</small>
            </div>
          </div>
        </Row>

        <Row token=".entry">
          <a className="entry" href="#/styleguide" style={{ minWidth: 420, margin: 0 }}>
            <span className="tags">
              <span className="code-chip">4.OA.A.3</span>
              <span className="tag">California</span>
              <span className="tag">Grade 4</span>
            </span>
            <p className="statement">
              Solve multistep word problems posed with whole numbers and having whole-number
              answers using the four operations.
            </p>
          </a>
        </Row>

        <Row token=".card-ruled">
          <div className="card-ruled" style={{ minWidth: 280 }}>
            <span className="verb-do">757</span>
            <h3 className="h3">Progressions live on the spine</h3>
            <p className="card-body">Every prerequisite edge is authored on Multi-State math.</p>
          </div>
        </Row>

        <Row token=".note / .error / .empty">
          <div style={{ display: 'grid', gap: 'var(--s-3)', minWidth: 380 }}>
            <Note text="Prerequisites were found on the aligned Multi-State standard." />
            <ErrorBox message="Could not reach the mirror. Is `learning-net web` still running?" />
            <Empty title="Nothing matches that wording.">
              <p style={{ margin: '6px 0 0' }}>Try fewer words, or a standard code.</p>
            </Empty>
          </div>
        </Row>

        <Row token=".loading-bar">
          <div style={{ minWidth: 320 }}>
            <Loading />
          </div>
        </Row>

        <Row token=".code + copy">
          <div style={{ minWidth: 420 }}>
            <CodeBlock code={'learning-net status\nlearning-net web --open'} />
          </div>
        </Row>

        <Row token=".eyebrow">
          <p className="eyebrow" style={{ margin: 0 }}>
            Self-hosted mirror · Open source
          </p>
        </Row>
      </Section>

      <Section title="The rule">
        <p className="prose">
          Solid means authored. Dashed means inferred. Brass belongs to the Multi-State spine and to
          anything that crossed it, and appears nowhere else — not as an accent, not as a highlight,
          not for emphasis. Blue means a person can interact with it. Every other decision in this
          system is negotiable; these are not.
        </p>
      </Section>
    </>
  )
}
