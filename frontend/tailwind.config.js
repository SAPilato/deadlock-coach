/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Atkinson Hyperlegible"', "system-ui", "Segoe UI", "sans-serif"],
      },
      colors: {
        bg: "#0e1014",
        panel: "#171a21",
        panel2: "#1f232c",
        line: "#2e3440",
        ink: "#f4f5f7",
        dim: "#b8bfcc",
        high: "#ff6b6b",
        med: "#ffc24b",
        low: "#6cc4ff",
        good: "#5ee08a",
        accent: "#c9a6ff",
      },
    },
  },
  plugins: [],
};
