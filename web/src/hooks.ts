import { useEffect, useRef, useState } from 'react'

/** Value that trails its input by `ms`, so typing does not fire a query per
 *  keystroke. 180ms is under the threshold where a local answer still feels
 *  instant, and this mirror answers in single-digit milliseconds. */
export function useDebounced<T>(value: T, ms = 180): T {
  const [held, setHeld] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setHeld(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return held
}

/** Arrow-key cursor over a result list.
 *
 *  Returns the index of the highlighted row and an onKeyDown to spread onto the
 *  input. Enter opens the highlighted row; Escape drops the cursor. The list
 *  resets to "nothing highlighted" whenever `length` changes, so a new set of
 *  results never inherits the previous position. */
export function useCursor(length: number, onOpen: (i: number) => void) {
  const [i, setI] = useState(-1)
  const open = useRef(onOpen)
  open.current = onOpen

  useEffect(() => {
    setI(-1)
  }, [length])

  const onKeyDown = (e: { key: string; preventDefault: () => void }) => {
    if (!length) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setI((n) => (n + 1) % length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setI((n) => (n <= 0 ? length - 1 : n - 1))
    } else if (e.key === 'Enter' && i >= 0) {
      e.preventDefault()
      open.current(i)
    } else if (e.key === 'Escape') {
      setI(-1)
    }
  }

  return { cursor: i, onKeyDown }
}
