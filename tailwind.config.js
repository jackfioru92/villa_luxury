/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        // Luxury villa palette - updated with new colors
        'primary': {
          50: '#f0f9f6',
          100: '#e0f2ec',
          200: '#c1e5d6',
          300: '#92d1b7',
          400: '#5bb691',
          500: '#3d9b73',
          600: '#2E4A46',
          700: '#254037',
          800: '#1f352e',
          900: '#192924',
          950: '#0d1512',
        },
        'secondary': {
          50: '#f7f7f7',
          100: '#ededed',
          200: '#d4d4d4',
          300: '#b3b3b3',
          400: '#8a8a8a',
          500: '#6b6b6b',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#1D1D1B',
          950: '#0a0a0a',
        },
        'tertiary': {
          50: '#fefdfb',
          100: '#fdf9f2',
          200: '#f9f0e1',
          300: '#f3e4c8',
          400: '#e9d09f',
          500: '#E7D4A2',
          600: '#d4c086',
          700: '#b8a46b',
          800: '#9c8957',
          900: '#827449',
          950: '#463d26',
        },
        'gold': {
          400: '#d4af37',
          500: '#c5a028',
          600: '#a68523',
        },
      },
      fontFamily: {
        'serif': ['Cormorant Garamond', 'Georgia', 'serif'],
        'sans': ['Poppins', 'system-ui', 'sans-serif'],
      },
      spacing: {
        '128': '32rem',
        '144': '36rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.5s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      fontSize: {
        'xs': '.75rem',
        'sm': '.875rem',
        'base': '1rem',
        'medium': '1.2rem', // Adjusted to ensure it differs from 'base'
        'lg': '1.125rem',
        'xl': '1.25rem',
        '2xl': '1.5rem',
        '3xl': '1.875rem',
        '4xl': '2.25rem',
        '5xl': '3rem',
        '6xl': '3.75rem',
        '7xl': '4.5rem',
        '8xl': '6rem',
        '9xl': '8rem',
      },
      fontWeight: {
        'thin': 100,
        'extralight': 200,
        'light': 300,
        'normal': 400,
        'medium': 550, // Updated from 500 to 550
        'semibold': 600,
        'bold': 700,
        'extrabold': 800,
        'black': 900,
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
}
