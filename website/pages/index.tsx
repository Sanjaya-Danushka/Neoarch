import { useEffect, useState } from 'react'
import Link from 'next/link'
import { supabase } from '../lib/supabase'
import Layout from '../components/Layout'
import type { Session, User } from '@supabase/supabase-js'

interface Favorite {
  id: string
  bundle_name: string
  item_count: number
  created_at: string
}

const features = [
  { icon: '📦', title: 'Pacman', desc: 'Native Arch Linux package manager integration' },
  { icon: '🏗️', title: 'AUR', desc: 'Access the Arch User Repository effortlessly' },
  { icon: '📱', title: 'Flatpak', desc: 'Sandboxed applications from Flathub' },
  { icon: '⚡', title: 'npm', desc: 'JavaScript packages from the npm registry' },
  { icon: '☁️', title: 'Cloud Sync', desc: 'Sync your favourite bundles across devices' },
  { icon: '🎨', title: 'Modern UI', desc: 'Beautiful PyQt6 interface with dark theme' },
]

export default function Home() {
  const [session, setSession] = useState<Session | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s)
      setUser(s?.user ?? null)
      if (s?.user) loadFavorites(s.user.id)
      else setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s)
      setUser(s?.user ?? null)
      if (s?.user) loadFavorites(s.user.id)
      else setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [])

  async function loadFavorites(userId: string) {
    setLoading(true)
    const { data } = await supabase
      .from('user_favorites')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
    if (data) setFavorites(data as Favorite[])
    setLoading(false)
  }

  return (
    <Layout session={session} user={user} onSignOut={() => supabase.auth.signOut()}>
      {session ? <Dashboard user={user} favorites={favorites} loading={loading} /> : <Landing />}
    </Layout>
  )
}

function Landing() {
  return (
    <>
      <section className="max-w-5xl mx-auto px-4 pt-20 pb-24 text-center">
        <h1 className="text-5xl md:text-6xl font-bold mb-4 tracking-tight">
          Modern Package Manager
          <br />
          <span className="text-neoarch-accent">for Arch Linux</span>
        </h1>
        <p className="text-lg text-neoarch-muted max-w-2xl mx-auto mb-8 leading-relaxed">
          NeoArch brings pacman, AUR, Flatpak, and npm together under one beautiful interface.
          Discover, install, and sync your packages seamlessly across machines.
        </p>
        <div className="flex items-center justify-center gap-4 flex-wrap">
          <a href="https://github.com/Sanjaya-Danushka/Neoarch/releases" className="btn-primary text-base">
            Download
          </a>
          <Link href="/features" className="btn-outline text-base">
            Explore Features
          </Link>
          <Link href="/login" className="btn-outline text-base">
            Sign In to Sync
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 pb-24">
        <h2 className="text-2xl font-semibold text-center mb-2">Everything in One Place</h2>
        <p className="text-neoarch-muted text-center mb-10 max-w-md mx-auto">
          Five package sources, one unified workflow
        </p>
        <div className="grid md:grid-cols-3 gap-4">
          {features.map((f) => (
            <div key={f.title} className="card hover:border-neoarch-accent/30 transition-colors group">
              <span className="text-3xl group-hover:scale-110 inline-block transition-transform">{f.icon}</span>
              <h3 className="text-lg font-semibold mt-3 mb-1">{f.title}</h3>
              <p className="text-sm text-neoarch-muted leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-neoarch-border py-20">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="text-2xl font-semibold mb-4">Cloud-Synced Favourites</h2>
          <p className="text-neoarch-muted mb-10 max-w-lg mx-auto">
            Save your favourite package bundles to the cloud and restore them on any machine.
            Perfect for fresh installs or syncing between machines.
          </p>
          <div className="grid sm:grid-cols-2 gap-4 text-left max-w-xl mx-auto">
            {[
              { step: '1', title: 'Sign In', desc: 'With your Google account' },
              { step: '2', title: 'Build Bundle', desc: 'Add packages in the desktop app' },
              { step: '3', title: 'Save to Cloud', desc: 'One click uploads everything' },
              { step: '4', title: 'Load Anywhere', desc: 'Restore on any machine instantly' },
            ].map((s) => (
              <div key={s.step} className="card flex items-start gap-3 py-4">
                <span className="bg-neoarch-accent text-neoarch-bg w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold">
                  {s.step}
                </span>
                <div>
                  <p className="font-medium text-sm">{s.title}</p>
                  <p className="text-xs text-neoarch-muted mt-0.5">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}

function Dashboard({ user, favorites, loading }: { user: User | null; favorites: Favorite[]; loading: boolean }) {
  return (
    <main className="max-w-4xl mx-auto px-4 py-12 w-full">
      <div className="flex items-center gap-4 mb-8">
        <img
          src={user?.user_metadata?.avatar_url || user?.user_metadata?.picture || ''}
          alt="Avatar"
          className="w-12 h-12 rounded-full border-2 border-neoarch-accent"
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
        />
        <div>
          <h1 className="text-xl font-semibold">{user?.user_metadata?.full_name}</h1>
          <p className="text-neoarch-muted text-sm">{user?.email}</p>
        </div>
      </div>

      <h2 className="text-lg font-semibold mb-4">Saved Favourites</h2>
      {loading ? (
        <p className="text-neoarch-muted">Loading...</p>
      ) : favorites.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-neoarch-muted mb-2">No favourites saved yet</p>
          <p className="text-sm text-neoarch-muted">
            Use the NeoArch desktop app to save package bundles and they will appear here.
          </p>
        </div>
      ) : (
        <div className="grid gap-3">
          {favorites.map((fav) => (
            <div key={fav.id} className="card flex items-center justify-between">
              <div>
                <p className="font-medium">{fav.bundle_name}</p>
                <p className="text-sm text-neoarch-muted">{fav.item_count} packages</p>
              </div>
              <span className="text-xs text-neoarch-muted">
                {new Date(fav.created_at).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
