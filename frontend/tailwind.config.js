/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Atkinson Hyperlegible"', "system-ui", "Segoe UI", "sans-serif"],
      },
      colors: {
        // Surfaces and ink (dark theme, high contrast)
        bg: "#0e1014",
        panel: "#171a21",
        panel2: "#1f232c",
        line: "#2e3440",
        ink: "#f4f5f7",
        dim: "#c3c2b7",
        muted: "#9a9890",
        // Status palette (validated): severity always ships with an icon + label
        high: "#d03b3b",
        med: "#ec835a",
        low: "#fab219",
        good: "#0ca30c",
        // Categorical slots 1-3 (validated all-pairs on #171a21) + diverging red pole
        s1: "#3987e5",
        s2: "#d95926",
        s3: "#199e70",
        neg: "#e66767",
        // Item categories (validated all-pairs): weapon, vitality, spirit
        cw: "#d95926",
        cv: "#199e70",
        cs: "#9085e9",
      },
    },
  },
  plugins: [],
};
