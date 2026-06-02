import Layout from '../components/Layout'
import Link from 'next/link'

const sections = [
  {
    icon: '📦',
    title: 'Multi-Repo Search',
    desc: 'Search pacman, AUR, Flatpak, and npm from a single search bar. Results are grouped by source with clear labels, versions, and descriptions.',
    highlights: ['Real-time search as you type', 'Source badges for each result', 'Version comparison across repos'],
  },
  {
    icon: '🏗️',
    title: 'AUR Helper Built-In',
    desc: 'No need for yay, paru, or any external AUR helper. NeoArch handles AUR builds directly with full PKGBUILD review before installation.',
    highlights: ['Automatic dependency resolution', 'PKGBUILD diff viewer', 'Build progress in real-time'],
  },
  {
    icon: '📱',
    title: 'Flatpak Integration',
    desc: 'Browse Flathub, install sandboxed applications, and manage runtimes — all without touching the flatpak CLI.',
    highlights: ['Flathub repository browser', 'Sandbox permission viewer', 'Runtime management'],
  },
  {
    icon: '☁️',
    title: 'Cloud Favourites',
    desc: 'Sign in with Google and sync your favourite package bundles across all your machines. No more re-discovering packages on every fresh install.',
    highlights: ['Google OAuth for easy sign-in', 'One-click save/load', 'Cross-machine sync via Supabase'],
  },
  {
    icon: '🎨',
    title: 'Modern Dark UI',
    desc: 'Built with PyQt6, NeoArch features a polished dark theme with smooth animations, a responsive layout, and keyboard shortcuts for power users.',
    highlights: ['Dark theme with accent colors', 'Grid and list views', 'Keyboard navigation'],
  },
  {
    icon: '👥',
    title: 'Community Bundles',
    desc: 'Share your favourite package combinations with the community. Discover curated bundles for development, gaming, design, and more.',
    highlights: ['Export/import bundle files', 'Community bundle directory', 'Curated by users'],
  },
]

export default function Features() {
  return (
    <Layout>
      <main className="max-w-4xl mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold mb-2">Features</h1>
          <p className="text-neoarch-muted max-w-lg mx-auto">
            Everything you need to manage packages on Arch Linux, all in one place
          </p>
        </div>

        <div className="grid gap-6">
          {sections.map((s) => (
            <div key={s.title} className="card md:flex items-start gap-6">
              <span className="text-3xl flex-shrink-0">{s.icon}</span>
              <div className="mt-3 md:mt-0">
                <h2 className="text-xl font-semibold mb-2">{s.title}</h2>
                <p className="text-sm text-neoarch-muted leading-relaxed mb-3">{s.desc}</p>
                <div className="flex flex-wrap gap-2">
                  {s.highlights.map((h) => (
                    <span key={h} className="text-xs bg-neoarch-surface text-neoarch-muted px-2.5 py-1 rounded-full border border-neoarch-border">
                      {h}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center mt-10">
          <a href="https://github.com/Sanjaya-Danushka/Neoarch/releases" className="btn-primary">
            Download NeoArch
          </a>
        </div>
      </main>
    </Layout>
  )
}
