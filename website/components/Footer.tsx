export default function Footer() {
  return (
    <footer className="border-t border-neoarch-border bg-neoarch-bg/80 backdrop-blur-md">
      <div className="max-w-5xl mx-auto px-4 py-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-neoarch-muted">
        <span>© {new Date().getFullYear()} NeoArch</span>
        <div className="flex items-center gap-4">
          <a href="https://github.com/sanjaya-danushka/Neoarch" target="_blank" rel="noopener noreferrer" className="hover:text-neoarch-text transition-colors">
            GitHub
          </a>
          <span>MIT License</span>
        </div>
      </div>
    </footer>
  )
}
