import { stats, useApi } from './api'
import { AboutPage } from './pages/AboutPage'
import { CoveragePage } from './pages/CoveragePage'
import { CrosswalkPage } from './pages/CrosswalkPage'
import { SearchPage } from './pages/SearchPage'
import { StandardPage } from './pages/StandardPage'
import { StatusPage } from './pages/StatusPage'
import { useRoute } from './router'

function Page({ path, params }: { path: string; params: URLSearchParams }) {
  if (path.startsWith('/standard/'))
    return <StandardPage id={decodeURIComponent(path.slice('/standard/'.length))} />
  if (path === '/crosswalk') return <CrosswalkPage params={params} />
  if (path === '/coverage') return <CoveragePage />
  if (path === '/status') return <StatusPage />
  // Search lived at #/ before About became the landing page; #/?q=… bookmarks
  // from then still deserve results, not a marketing page.
  if (path === '/search' || (path === '/' && params.has('q')))
    return <SearchPage params={params} />
  return <AboutPage />
}

const NAV: [href: string, label: string, path: string][] = [
  ['#/search', 'Search', '/search'],
  ['#/crosswalk', 'Crosswalk', '/crosswalk'],
  ['#/coverage', 'Coverage', '/coverage'],
  ['#/status', 'Status', '/status'],
]

export default function App() {
  const route = useRoute()
  const s = useApi(stats, [])
  const version = s.data?.snapshot?.kgVersion
  const isSearch =
    route.path === '/search' ||
    route.path.startsWith('/standard/') ||
    (route.path === '/' && route.params.has('q'))
  const active = isSearch ? '/search' : route.path === '/about' ? '/' : route.path
  return (
    <>
      <header className="topbar">
        <a className="wordmark" href="#/">
          Learning Net
        </a>
        <nav aria-label="Main">
          {NAV.map(([href, label, path]) => (
            <a key={path} href={href} aria-current={active === path ? 'page' : undefined}>
              {label}
            </a>
          ))}
        </nav>
        <span className="topbar-right">
          <a href="#/" aria-current={active === '/' ? 'page' : undefined}>
            About
          </a>
          {version && (
            <a
              className="version"
              href="#/status"
              title="Upstream release this mirror was built from"
            >
              KG v{version}
            </a>
          )}
        </span>
      </header>
      <main className="container">
        <Page path={route.path} params={route.params} />
      </main>
      <footer className="footer">
        A self-hosted mirror of the{' '}
        <a href="https://www.learningcommons.org" rel="noreferrer">
          Learning Commons
        </a>{' '}
        Knowledge Graph · data CC BY-4.0, attribution preserved on every node
      </footer>
    </>
  )
}
