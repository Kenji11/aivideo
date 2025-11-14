/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        // Light mode colors
        primary: {
          DEFAULT: '#3B82F6',
          hover: '#2563EB',
        },
        // Dark mode colors (handled by dark: prefix)
      },
    },
  },
  plugins: [],
}
