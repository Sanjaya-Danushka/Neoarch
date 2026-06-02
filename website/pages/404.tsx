import Layout from '../components/Layout'
import Link from 'next/link'

export default function Custom404() {
  return (
    <Layout>
      <main className="max-w-lg mx-auto px-4 py-20 text-center">
        <div className="text-8xl mb-4">404</div>
        <p className="text-2xl font-semibold mb-2">Package Not Found</p>
        <p className="text-neoarch-muted mb-2">
          This page doesn't exist in any configured repository.
        </p>
        <p className="text-sm text-neoarch-muted mb-8 italic">
          Try <span className="text-neoarch-accent not-italic">sudo pacman -S</span> common-sense? No? Okay.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link href="/" className="btn-primary">Go Home</Link>
          <Link href="/docs" className="btn-outline">Read the Docs</Link>
        </div>
        <p className="text-xs text-neoarch-muted mt-8">
          Or as we say in Arch: <span className="text-neoarch-accent">¯\_(ツ)_/¯</span>
        </p>
      </main>
    </Layout>
  )
}
