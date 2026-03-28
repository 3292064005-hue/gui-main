/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        clinical: {
          bg: '#0A0F1A',
          panel: '#151C2C',
          glass: 'rgba(21, 28, 44, 0.45)',
          cyan: '#00E5FF',
          emerald: '#00FA9A',
          amber: '#FFB800',
          error: '#FF2A55',
          surface: '#1A2235',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-fast': 'pulse 1.2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      backdropBlur: {
        '3xl': '64px',
      }
    },
  },
  plugins: [],
}
