import { stats, useApi } from './api'
import { AboutPage } from './pages/AboutPage'
import { CrosswalkPage } from './pages/CrosswalkPage'
import { SearchPage } from './pages/SearchPage'
import { StandardPage } from './pages/StandardPage'
import { StatusPage } from './pages/StatusPage'
import { useRoute } from './router'

function Page({ path, params }: { path: string; params: URLSearchParams }) {
  if (path.startsWith('/standard/'))
    return <StandardPage id={decodeURIComponent(path.slice('/standard/'.length))} />
  if (path === '/crosswalk') return <CrosswalkPage params={params} />
  if (path === '/status') return <StatusPage />
  if (path === '/about') return <AboutPage />
  return <SearchPage params={params} />
}

const NAV: [href: string, label: string, path: string][] = [
  ['#/', 'Search', '/'],
  ['#/crosswalk', 'Crosswalk', '/crosswalk'],
  ['#/status', 'Status', '/status'],
]

export default function App() {
  const route = useRoute()
  const s = useApi(stats, [])
  const version = s.data?.snapshot?.kgVersion
  const active = route.path.startsWith('/standard/') ? '/' : route.path
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
          <a href="#/about" aria-current={active === '/about' ? 'page' : undefined}>
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
