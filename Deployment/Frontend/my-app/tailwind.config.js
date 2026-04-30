/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['"DM Sans"', 'sans-serif'],
      },
      colors: {
        terminal: {
          bg:      '#0a0a0f',
          surface: '#111118',
          card:    '#16161e',
          border:  '#1e1e2e',
          hover:   '#1a1a24',
        },
        accent: {
          buy:    '#00d97e',
          sell:   '#ff4d6d',
          hold:   '#6b7280',
          info:   '#38bdf8',
          warn:   '#fbbf24',
        }
      },
      keyframes: {
        pulse_dot: {
          '0%, 100%': { opacity: 1 },
          '50%':      { opacity: 0.3 },
        },
        slide_up: {
          from: { opacity: 0, transform: 'translateY(8px)' },
          to:   { opacity: 1, transform: 'translateY(0)' },
        },
        fade_in: {
          from: { opacity: 0 },
          to:   { opacity: 1 },
        }
      },
      animation: {
        pulse_dot: 'pulse_dot 1.5s ease-in-out infinite',
        slide_up:  'slide_up 0.3s ease forwards',
        fade_in:   'fade_in 0.4s ease forwards',
      }
    }
  },
  plugins: []
}