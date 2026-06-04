import Link from 'next/link'
import Image from 'next/image'

export default function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-neoarch-bg/80 backdrop-blur-md border-b border-neoarch-border">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 group">
          <Image src="/logo.png" alt="NeoArch" width={28} height={28} className="rounded-md" />
          <span className="font-semibold text-lg text-neoarch-text group-hover:text-neoarch-accent transition-colors">
            NeoArch
          </span>
        </Link>
        <nav className="flex items-center gap-4 text-sm text-neoarch-muted">
          <a href="https://github.com/sanjaya-danushka/Neoarch" target="_blank" rel="noopener noreferrer" className="hover:text-neoarch-text transition-colors">
            GitHub
          </a>
        </nav>
      </div>
    </header>
  )
}
