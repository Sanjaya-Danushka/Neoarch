import Link from 'next/link'
import { supabase } from '../lib/supabase'
import { useEffect, useState } from 'react'
import type { Session, User } from '@supabase/supabase-js'

interface LayoutProps {
  children: React.ReactNode
  session?: Session | null
  user?: User | null
  onSignOut?: () => void
}

export default function Layout({ children, session: propSession, user: propUser, onSignOut }: LayoutProps) {
  const [session, setSession] = useState<Session | null>(propSession || null)
  const [user, setUser] = useState<User | null>(propUser || null)

  useEffect(() => {
    if (propSession === undefined) {
      supabase.auth.getSession().then(({ data: { session: s } }) => {
        setSession(s)
        setUser(s?.user ?? null)
      })
    }
  }, [])

  const handleSignOut = onSignOut || (async () => {
    await supabase.auth.signOut()
  })

  return (
    <div className="min-h-screen bg-neoarch-bg text-neoarch-text flex flex-col">
      {/* Navbar */}
      <nav className="border-b border-neoarch-border bg-neoarch-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2 font-bold text-lg">
              <span className="text-neoarch-accent">◆</span>
              NeoArch
            </Link>
            <div className="hidden md:flex items-center gap-4 text-sm text-neoarch-muted">
              <Link href="/features" className="hover:text-neoarch-text transition-colors">Features</Link>
              <Link href="/docs" className="hover:text-neoarch-text transition-colors">Docs</Link>
              <Link href="/about" className="hover:text-neoarch-text transition-colors">About</Link>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {session ? (
              <div className="flex items-center gap-3">
                <span className="text-sm text-neoarch-muted hidden sm:block">{user?.email}</span>
                {user?.user_metadata?.avatar_url && (
                  <img
                    src={user.user_metadata.avatar_url}
                    alt=""
                    className="w-7 h-7 rounded-full border border-neoarch-accent/50"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                )}
                <button onClick={handleSignOut} className="btn-outline text-sm py-1.5 px-3">Sign Out</button>
              </div>
            ) : (
              <Link href="/login" className="btn-primary text-sm py-1.5">Sign In</Link>
            )}
          </div>
        </div>
      </nav>

      {children}

      {/* Footer */}
      <footer className="border-t border-neoarch-border mt-auto">
        <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-neoarch-muted">
          <p>Built with ❤️ for the Arch Linux community</p>
          <div className="flex items-center gap-6">
            <Link href="/about" className="hover:text-neoarch-text transition-colors">About</Link>
            <a href="https://github.com/Sanjaya-Danushka/Neoarch" className="hover:text-neoarch-text transition-colors">GitHub</a>
            <a href="https://github.com/Sanjaya-Danushka/Neoarch/issues" className="hover:text-neoarch-text transition-colors">Issues</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
