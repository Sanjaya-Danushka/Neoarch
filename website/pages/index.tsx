import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { User, Session } from '@supabase/supabase-js'

interface Favorite {
  id: string
  bundle_name: string
  item_count: number
  created_at: string
}

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

  const handleSignOut = async () => {
    await supabase.auth.signOut()
  }

  if (!session) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <h1 style={styles.title}>NeoArch</h1>
          <p style={styles.subtitle}>Sign in to sync your favourite packages</p>
          <a href="/login" style={styles.button}>Sign in with Google</a>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.header}>
          <img
            src={user?.user_metadata?.avatar_url || ''}
            alt="Avatar"
            style={styles.avatar}
          />
          <div>
            <h2 style={{ margin: 0, fontSize: 18 }}>{user?.user_metadata?.full_name}</h2>
            <p style={{ margin: 0, color: '#9CA3AF', fontSize: 14 }}>{user?.email}</p>
          </div>
        </div>

        <h3 style={{ marginTop: 24, marginBottom: 12, fontSize: 16 }}>Saved Favourites</h3>
        {loading ? (
          <p style={{ color: '#6B7280' }}>Loading...</p>
        ) : favorites.length === 0 ? (
          <p style={{ color: '#6B7280', fontSize: 14 }}>
            No favourites saved yet. Use the NeoArch desktop app to save package bundles.
          </p>
        ) : (
          <div style={styles.list}>
            {favorites.map((fav) => (
              <div key={fav.id} style={styles.listItem}>
                <strong style={{ fontSize: 14 }}>{fav.bundle_name}</strong>
                <span style={{ color: '#9CA3AF', fontSize: 13 }}>{fav.item_count} packages</span>
              </div>
            ))}
          </div>
        )}

        <button onClick={handleSignOut} style={styles.outBtn}>Sign Out</button>
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
    padding: 40,
    maxWidth: 480,
    width: '90%',
    border: '1px solid #2a2a2a',
  },
  title: {
    fontSize: 28,
    fontWeight: 700,
    margin: '0 0 8px',
  },
  subtitle: {
    color: '#9CA3AF',
    margin: '0 0 24px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginBottom: 20,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
  },
  button: {
    display: 'inline-block',
    background: '#00BFAE',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '12px 24px',
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    textDecoration: 'none',
  },
  outBtn: {
    background: 'transparent',
    color: '#9CA3AF',
    border: '1px solid #333',
    borderRadius: 8,
    padding: '8px 16px',
    fontSize: 13,
    cursor: 'pointer',
    marginTop: 20,
    width: '100%',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  listItem: {
    background: '#0f0f0f',
    borderRadius: 8,
    padding: '12px 16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
}
