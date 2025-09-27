import type { Config } from 'tailwindcss'

const config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          background: '#050915',
        },
      },
      boxShadow: {
        message: '0 12px 32px rgba(15, 23, 42, 0.45)',
      },
      backgroundImage: {
        'hero-accent': 'radial-gradient(circle, rgba(59, 130, 246, 0.25), transparent 70%)',
        'app-backdrop':
          'radial-gradient(circle at top, rgba(56, 189, 248, 0.25), transparent 55%), radial-gradient(circle at bottom, rgba(168, 85, 247, 0.2), transparent 60%)',
      },
    },
  },
  plugins: [],
} satisfies Config

export default config
