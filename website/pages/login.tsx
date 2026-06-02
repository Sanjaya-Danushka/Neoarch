import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import Header from '../components/Header'
import Footer from '../components/Footer'

export default function LoginPage() {
  const [callbackUrl, setCallbackUrl] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const cb = params.get('callback') || ''
    if (cb) setCallbackUrl(cb)
  }, [])

  const handleGoogleSignIn = async () => {
    setError(null)
    try {
      const base = window.location.pathname.replace(/\/login\/?$/, '') || ''
      const redirectTo = callbackUrl
        ? `${window.location.origin}${base}/auth/callback?callback=${encodeURIComponent(callbackUrl)}`
        : `${window.location.origin}${base}/auth/callback`

      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo },
      })
      if (error) setError(error.message)
    } catch (e: any) {
      setError(e?.message || 'Failed to start sign in')
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-neoarch-bg">
      <Header />

      <main className="flex-1 flex items-center justify-center px-4 pt-14">
        <div className="card w-full max-w-sm py-12 px-8 text-center">
          <img src="/logo.png" alt="NeoArch" className="w-16 h-16 mx-auto mb-4 rounded-xl" />
          <h1 className="text-2xl font-bold mb-1">NeoArch</h1>
          <p className="text-neoarch-muted text-sm mb-8">Sign in to sync your package favourites</p>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2.5 text-sm text-red-300 mb-4">
              {error}
            </div>
          )}

          <button
            onClick={handleGoogleSignIn}
            className="flex items-center justify-center w-full bg-white hover:bg-gray-100 text-neoarch-bg font-semibold rounded-lg px-6 py-3 transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" className="mr-3 flex-shrink-0">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
          </button>

          {callbackUrl && (
            <div className="mt-6 p-3 rounded-lg bg-neoarch-accent/10 border border-neoarch-accent/20">
              <div className="flex items-center justify-center gap-2 text-neoarch-accent mb-1">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
                <span className="text-xs font-medium">Redirecting back to app</span>
              </div>
              <p className="text-xs text-neoarch-muted break-all">
                {callbackUrl}
              </p>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  )
}
