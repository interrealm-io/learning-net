// Hash routing keeps the Python server route-free: every path serves the app
// shell and the client decides what to show. ~30 lines instead of a router dep.

import { useEffect, useState } from 'react'

export interface Route {
  path: string
  params: URLSearchParams
}

function parse(): Route {
  const raw = location.hash.replace(/^#/, '') || '/'
  const [path, query = ''] = raw.split('?')
  return { path, params: new URLSearchParams(query) }
}

export function useRoute(): Route {
  const [route, setRoute] = useState(parse)
  useEffect(() => {
    const onChange = () => setRoute(parse())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

export function navigate(to: string) {
  location.hash = to
}

export const standardHref = (id: string) => `#/standard/${encodeURIComponent(id)}`
