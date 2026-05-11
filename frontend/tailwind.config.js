/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        wood: {
          50: '#fdf8f0',
          100: '#f9edda',
          500: '#8B5E3C',
          600: '#6B4226',
          700: '#4A2C14',
        },
      },
    },
  },
  plugins: [],
}
