export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-neoarch-bg px-4">
      <div className="card w-full max-w-sm py-10 px-8 text-center">
        <div className="text-5xl text-neoarch-accent mb-2">◆</div>
        <h1 className="text-2xl font-bold mb-1">NeoArch</h1>
        <p className="text-neoarch-muted text-sm mb-8">
          Package manager cloud sync
        </p>
        <a href="/login" className="btn-primary inline-block w-full text-center">
          Sign In with Google
        </a>
      </div>
    </div>
  )
}
