/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        neoarch: {
          bg: '#0F1117',
          card: '#1A1C25',
          border: '#2A2D3A',
          accent: '#00BFAE',
          'accent-hover': '#00D4C4',
          text: '#F0F0F0',
          muted: '#8B8FA3',
          surface: '#252836',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
