/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#eefcf3",
          100: "#d6f7e2",
          500: "#1a9d5c",   // primary Saaransh green (buttons, active nav, accents)
          600: "#158049",
          700: "#106339",
        },
        risk: {
          veryhigh: "#dc2626",
          high:     "#f97316",
          medium:   "#eab308",
          low:      "#84cc16",
          verylow:  "#22c55e",
        },
        ink: {
          900: "#0f172a",
          800: "#1e293b",
          700: "#334155",
          600: "#475569",
          500: "#64748b",
          400: "#94a3b8",
          300: "#cbd5e1",
          200: "#e2e8f0",
          100: "#f1f5f9",
          50:  "#f8fafc",
        }
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,23,42,0.06), 0 1px 3px rgba(15,23,42,0.08)",
      },
      borderRadius: {
        xl2: "1rem",
      }
    },
  },
  plugins: [],
}
