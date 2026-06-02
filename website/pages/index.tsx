import Header from '../components/Header'
import Footer from '../components/Footer'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col bg-neoarch-bg">
      <Header />

      <main className="flex-1 flex items-center justify-center px-4 pt-14">
        <div className="card w-full max-w-sm py-12 px-8 text-center">
          <img src="/logo.png" alt="NeoArch" className="w-16 h-16 mx-auto mb-4 rounded-xl" />
          <h1 className="text-2xl font-bold mb-1">NeoArch</h1>
          <p className="text-neoarch-muted text-sm mb-8">
            Package manager cloud sync
          </p>
          <a href="/login" className="btn-primary inline-block w-full text-center">
            Sign In with Google
          </a>
        </div>
      </main>

      <Footer />
    </div>
  )
}
