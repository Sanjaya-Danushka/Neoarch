import Layout from '../components/Layout'
import Link from 'next/link'

const steps = [
  {
    title: 'Installation',
    content: [
      'Download the latest release from GitHub Releases.',
      'Extract the archive: tar -xzf NeoArch-*.tar.gz',
      'Run: cd NeoArch && pip install -r requirements_pyqt.txt',
      'Launch: python3 NeoArch.py',
      'Or install via the AUR (coming soon).',
    ],
  },
  {
    title: 'Finding Packages',
    content: [
      'Type in the search bar at the top of the app.',
      'Results appear from pacman, AUR, Flatpak, and npm simultaneously.',
      'Use the source filters on the left to narrow by repository.',
      'Click a package to see details, version info, and description.',
    ],
  },
  {
    title: 'Installing Packages',
    content: [
      'Check the box next to any package you want to install.',
      'Click the "Install" button in the top toolbar.',
      'NeoArch handles dependencies and shows progress.',
      'AUR packages will show the PKGBUILD for review before building.',
    ],
  },
  {
    title: 'Building a Bundle',
    content: [
      'Switch to the "Bundles" view from the sidebar.',
      'Search and add packages to your bundle.',
      'Export your bundle as a JSON file to share or back up.',
      'Save it to the cloud with one click (requires sign-in).',
    ],
  },
  {
    title: 'Cloud Sync',
    content: [
      'Click your avatar in the bottom-left corner of the sidebar.',
      'Select "Sign In" to authenticate with Google.',
      'Once signed in, use "Save to Cloud" / "Load from Cloud" in the Bundle toolbar.',
      'Your favourites are now available on any machine.',
    ],
  },
  {
    title: 'Community Bundles',
    content: [
      'Select packages in your bundle and click "Add to Community".',
      'Browse community bundles from the Community section.',
      'Import a community bundle to add those packages to your setup.',
      'Share your own curated lists with the community.',
    ],
  },
]

export default function Docs() {
  return (
    <Layout>
      <main className="max-w-3xl mx-auto px-4 py-16">
        <h1 className="text-3xl font-bold mb-2">Documentation</h1>
        <p className="text-neoarch-muted mb-10">Everything you need to get started with NeoArch</p>

        <div className="space-y-6">
          {steps.map((section, i) => (
            <div key={section.title} className="card">
              <div className="flex items-center gap-3 mb-3">
                <span className="bg-neoarch-accent text-neoarch-bg w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold">
                  {i + 1}
                </span>
                <h2 className="text-lg font-semibold">{section.title}</h2>
              </div>
              <ol className="space-y-2 ml-10">
                {section.content.map((line, j) => (
                  <li key={j} className="text-sm text-neoarch-muted leading-relaxed list-disc marker:text-neoarch-accent">
                    {line}
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>

        <div className="card mt-8 text-center py-6">
          <p className="text-sm text-neoarch-muted mb-3">Need more help?</p>
          <a href="https://github.com/Sanjaya-Danushka/Neoarch/issues" className="btn-outline text-sm">
            Open a GitHub Issue
          </a>
        </div>
      </main>
    </Layout>
  )
}
