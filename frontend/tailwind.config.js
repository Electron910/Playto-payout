/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        playto: {
          light: '#E8EDF2',
          dark: '#2C3947',
          blue: '#547A95',
          gold: '#C2A56D',
        },
      },
    },
  },
  plugins: [],
}