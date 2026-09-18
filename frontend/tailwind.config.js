/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        tactical: {
          bg: "#080b11",
          surface: "#0e131d",
          panel: "#141b29",
          border: "#1e293b",
          accent: "#00ffc8",
          warning: "#f59e0b",
          danger: "#ef4444",
          info: "#38bdf8",
          dim: "#64748b"
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif']
      }
    },
  },
  plugins: [],
}
