import Layout from '../components/Layout'
import Link from 'next/link'

export default function About() {
  return (
    <Layout>
      <main className="max-w-3xl mx-auto px-4 py-16">
        <h1 className="text-3xl font-bold mb-2">About NeoArch</h1>
        <p className="text-neoarch-muted mb-10">The story behind the package manager</p>

        <section className="space-y-8">
          <div className="card">
            <h2 className="text-lg font-semibold mb-2">Why Another Package Manager?</h2>
            <p className="text-sm text-neoarch-muted leading-relaxed">
              Arch Linux already has the best package manager (pacman). The AUR has everything else.
              Flatpak handles sandboxed apps. npm has... well, everything JavaScript.
            </p>
            <p className="text-sm text-neoarch-muted leading-relaxed mt-3">
              NeoArch doesn't replace any of them. It wraps them all in a single, friendly GUI
              so you don't have to remember five different commands every time you want to install something.
            </p>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold mb-2">The Philosophy</h2>
            <ul className="space-y-3 text-sm text-neoarch-muted">
              {[
                ['🎯', 'One interface to rule them all', 'pacman, AUR, Flatpak, npm — same UI'],
                ['☁️', 'Your config follows you', 'Favourites sync to the cloud via Google login'],
                ['🎨', 'Good looks are not optional', 'PyQt6 dark theme that respects your eyes'],
                ['🐍', 'Python-powered', 'Built with Python and PyQt6, easy to hack on'],
                ['📦', 'Community bundles', 'Share your favourite package lists with others'],
              ].map(([icon, title, desc]) => (
                <li key={title} className="flex items-start gap-3">
                  <span className="text-lg flex-shrink-0">{icon}</span>
                  <div>
                    <p className="text-neoarch-text font-medium">{title}</p>
                    <p className="text-neoarch-muted text-xs mt-0.5">{desc}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold mb-2">Wait, Is This Stable?</h2>
            <p className="text-sm text-neoarch-muted leading-relaxed">
              NeoArch is a passion project — it works, it's functional, and it's used daily.
              But it's also a single-developer project built for learning and scratching an itch.
              If something breaks, you get to keep both pieces.
            </p>
            <p className="text-sm text-neoarch-muted leading-relaxed mt-3">
              <span className="text-neoarch-accent">The good news:</span> NeoArch just wraps existing
              package managers. If something goes wrong, you can always fall back to pacman/AUR/Flatpak/npm directly.
              Your system stays safe.
            </p>
          </div>

          <div className="card text-center py-8">
            <span className="text-4xl">🐧</span>
            <p className="text-neoarch-muted text-sm mt-3">
              Built on Arch Linux. For Arch Linux. Because <span className="text-neoarch-accent italic">btw I use Arch</span>.
            </p>
          </div>
        </section>

        <div className="text-center mt-10">
          <Link href="/docs" className="btn-primary">Get Started</Link>
        </div>
      </main>
    </Layout>
  )
}
