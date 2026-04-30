/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        mono: ['"IBM Plex Mono"', 'monospace'],
        sans: ['"IBM Plex Sans"', 'sans-serif'],
      },
      colors: {
        bg:      '#0a0906',
        bg1:     '#0f0d0a',
        bg2:     '#141210',
        bg3:     '#1c1916',
        bg4:     '#242018',
        border:  '#2a2520',
        border2: '#3a332a',
        amber:   '#e8a030',
        amber2:  '#c8841a',
        text:    '#e8e0d0',
        text2:   '#a09080',
        text3:   '#605848',
        green:   '#3db87a',
        red:     '#d45c4a',
        blue:    '#5a9fd4',
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
        },
        price_flash_green: {
          '0%':   { backgroundColor: 'rgba(61, 184, 122, 0.2)' },
          '100%': { backgroundColor: 'transparent' },
        },
        price_flash_red: {
          '0%':   { backgroundColor: 'rgba(212, 92, 74, 0.2)' },
          '100%': { backgroundColor: 'transparent' },
        }
      },
      animation: {
        pulse_dot: 'pulse_dot 1.5s ease-in-out infinite',
        slide_up:  'slide_up 0.3s ease forwards',
        fade_in:   'fade_in 0.4s ease forwards',
        flash_green: 'price_flash_green 0.6s ease',
        flash_red:   'price_flash_red 0.6s ease',
      }
    }
  },
  plugins: []
}