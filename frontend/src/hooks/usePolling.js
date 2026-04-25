import { useState, useEffect, useCallback, useRef } from 'react'

export default function usePolling(fetchFn, intervalMs = 4000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)
  const mountedRef = useRef(true)

  const refresh = useCallback(() => {
    fetchFn()
      .then((result) => {
        if (mountedRef.current) {
          setData(result)
          setError(null)
        }
      })
      .catch((err) => {
        if (mountedRef.current) {
          setError(err)
        }
      })
      .finally(() => {
        if (mountedRef.current) {
          setLoading(false)
        }
      })
  }, [fetchFn])

  useEffect(() => {
    mountedRef.current = true
    setLoading(true)
    refresh()

    intervalRef.current = setInterval(refresh, intervalMs)

    return () => {
      mountedRef.current = false
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [refresh, intervalMs])

  return { data, loading, error, refresh }
}