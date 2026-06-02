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
    <div className="min-h-screen flex items-center justify-center bg-neoarch-bg">
      <div className="card text-center py-10 px-8">
        <div className="text-4xl text-neoarch-accent mb-3 animate-pulse">◆</div>
        <p className="text-neoarch-text">{status}</p>
      </div>
    </div>
  )
}
