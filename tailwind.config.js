/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js",
    "./core/templates/**/*.html",
    "./levels/templates/**/*.html",
    "./**/*.html",
    "./**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        'brand-dark': '#0D1117',
        'brand-surface': '#161B22',
        'brand-border': '#30363D',
        'brand-primary': '#2F81F7',
        'brand-primary-hover': '#58A6FF',
        'brand-secondary': '#8B949E',
        'brand-text': '#C9D1D9',
      }
    },
  },
  plugins: [],
} 