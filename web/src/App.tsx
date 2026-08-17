import { stats, useApi } from './api'
import { AboutPage } from './pages/AboutPage'
import { CoveragePage } from './pages/CoveragePage'
import { CrosswalkPage } from './pages/CrosswalkPage'
import { DocsPage } from './pages/DocsPage'
import { HomePage } from './pages/HomePage'
import { McpPage } from './pages/McpPage'
import { SearchPage } from './pages/SearchPage'
import { StandardPage } from './pages/StandardPage'
import { StatusPage } from './pages/StatusPage'
import { StyleguidePage } from './pages/StyleguidePage'
import { useRoute } from './router'

function Page({ path, params }: { path: string; params: URLSearchParams }) {
  if (path.startsWith('/standard/'))
    return <StandardPage id={decodeURIComponent(path.slice('/standard/'.length))} />
  if (path === '/crosswalk') return <CrosswalkPage params={params} />
  if (path === '/coverage') return <CoveragePage />
  if (path === '/status') return <StatusPage />
  if (path === '/docs') return <DocsPage />
  if (path === '/mcp') return <McpPage />
  if (path === '/styleguide') return <StyleguidePage />
  if (path === '/about') return <AboutPage />
  // Search lived at #/ before the home page existed; #/?q=… bookmarks from
  // then still deserve results, not a landing page.
  if (path === '/search' || (path === '/' && params.has('q')))
    return <SearchPage key={params.toString()} params={params} />
  return <HomePage />
}

const NAV: [href: string, label: string, path: string][] = [
  ['#/search', 'Search', '/search'],
  ['#/crosswalk', 'Crosswalk', '/crosswalk'],
  ['#/coverage', 'Coverage', '/coverage'],
  ['#/docs', 'Docs', '/docs'],
  ['#/mcp', 'MCP', '/mcp'],
  ['#/status', 'Status', '/status'],
  ['#/about', 'About', '/about'],
]

export default function App() {
  const route = useRoute()
  const s = useApi(stats, [])
  const version = s.data?.snapshot?.kgVersion
  const isSearch =
    route.path === '/search' ||
    route.path.startsWith('/standard/') ||
    (route.path === '/' && route.params.has('q'))
  const active = isSearch ? '/search' : route.path
  const isHome = route.path === '/' && !route.params.has('q')

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <header className="topbar">
        <div className="topbar-inner">
          <a className="wordmark" href="#/">
            {/* Two nodes, one dashed hop: authored on the left, inferred on the
                right. The same figure the whole interface argues for. */}
            <svg width="18" height="18" viewBox="0 0 32 32" aria-hidden="true">
              <path d="M11 19 21 13" stroke="#C9A24B" strokeWidth="2.5" strokeDasharray="3 3" />
              <circle cx="8" cy="22" r="5" fill="#FAF9F6" />
              <circle cx="24" cy="10" r="5" fill="#2457D6" />
            </svg>
            <span className="wordmark-name">Learning Net</span>
            <span className="wordmark-kicker">MIRROR</span>
          </a>

          <nav aria-label="Main">
            {NAV.map(([href, label, path]) => (
              <a key={path} href={href} aria-current={active === path ? 'page' : undefined}>
                {label}
              </a>
            ))}
            {version && (
              <a
                className="version-pill"
                href="#/status"
                title="Upstream release this mirror was built from"
              >
                KG v{version}
              </a>
            )}
          </nav>
        </div>
      </header>

      <main id="main">
        {isHome ? (
          <Page path={route.path} params={route.params} />
        ) : (
          <div className="container">
            <Page path={route.path} params={route.params} />
          </div>
        )}
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <span>
            A self-hosted mirror of the{' '}
            <a href="https://www.learningcommons.org" rel="noreferrer">
              Learning Commons
            </a>{' '}
            Knowledge Graph · data CC BY-4.0, attribution preserved on every node · code
            Apache-2.0, stewarded by the{' '}
            <a href="https://interrealm.org" rel="noreferrer">
              InterRealm Foundation
            </a>
          </span>
          <a className="footer-mono" href="#/styleguide">
            STYLE GUIDE
          </a>
        </div>
      </footer>
    </div>
  )
}
