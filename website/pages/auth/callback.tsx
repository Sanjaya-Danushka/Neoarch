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

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
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

    return () => {
      subscription?.unsubscribe()
    }
  }, [router.isReady, router.query])

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0F1117]">
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,191,174,0.08),transparent_70%)]" />
        <div className="absolute -left-20 top-40 h-72 w-72 glass-bubble animate-float" style={{ animationDelay: "0s" }} />
        <div className="absolute -right-10 top-20 h-96 w-96 glass-bubble animate-float-slow" style={{ animationDelay: "1s" }} />
        <div className="absolute bottom-20 left-1/3 h-48 w-48 glass-bubble animate-float" style={{ animationDelay: "2s" }} />
      </div>

      <div className="glass-card text-center">
        <div className="mb-4 flex justify-center">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-400 via-cyan-300 to-blue-500 flex items-center justify-center shadow-lg">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0F1117" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="animate-spin">
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
          </div>
        </div>
        <p className="text-[#F0F0F0] text-sm font-medium">{status}</p>
      </div>
    </div>
  )
}
