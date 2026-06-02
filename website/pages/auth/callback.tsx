import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import { supabase } from '../../lib/supabase'

export default function AuthCallback() {
  const router = useRouter()
  const [status, setStatus] = useState('Completing sign in...')

  useEffect(() => {
    if (!router.isReady) return

    const { callback } = router.query
    const desktopCallback = (callback as string) || ''

    supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        setStatus('Signed in! Redirecting to app...')

        if (desktopCallback) {
          const accessToken = session.access_token
          const refreshToken = session.refresh_token
          const redirectUrl = `${desktopCallback}?access_token=${accessToken}&refresh_token=${refreshToken}`
          window.location.href = redirectUrl
        } else {
          router.push('/')
        }
      }
    })

    // Exchange the auth code for a session if needed
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session && desktopCallback) {
        const accessToken = session.access_token
        const refreshToken = session.refresh_token
        const redirectUrl = `${desktopCallback}?access_token=${accessToken}&refresh_token=${refreshToken}`
        window.location.href = redirectUrl
      } else if (session) {
        router.push('/')
      }
    })
  }, [router.isReady, router.query])

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <p style={styles.text}>{status}</p>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#0a0a0a',
    color: '#fff',
    fontFamily: 'system-ui, sans-serif',
  },
  card: {
    background: '#1a1a1a',
    borderRadius: 16,
    padding: 48,
    border: '1px solid #2a2a2a',
    textAlign: 'center',
  },
  text: {
    fontSize: 18,
    color: '#D1D5DB',
  },
}
