import type { AppProps } from 'next/app'
import Head from 'next/head'
import '../styles/globals.css'
import { assetUrl } from '../lib/path'

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>NeoArch — Modern Arch Linux Package Manager</title>
        <meta name="description" content="NeoArch: A modern GUI package manager for Arch Linux with multi-repo support (pacman, AUR, Flatpak, npm) and cloud-synced favourites." />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <link rel="icon" href={assetUrl('/logo.png')} />
      </Head>
      <Component {...pageProps} />
    </>
  )
}
