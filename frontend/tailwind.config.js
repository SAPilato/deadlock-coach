/** @type {import('tailwindcss').Config} */

// Every colour is a theme variable (see src/index.css), stored as "R G B" so
// Tailwind's opacity modifiers (bg-panel/80) keep working.
const token = (name) => `rgb(var(--c-${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-body)"],
        display: ["var(--font-display)"],
      },
      borderRadius: {
        lg: "var(--r-lg)",
        xl: "var(--r-xl)",
        "2xl": "var(--r-2xl)",
      },
      colors: {
        // Surfaces and ink
        bg: token("bg"),
        panel: token("panel"),
        panel2: token("panel2"),
        line: token("line"),
        ink: token("ink"),
        dim: token("dim"),
        muted: token("muted"),
        // UI accent (links, buttons, focus, selection) and the text that sits on it
        accent: token("accent"),
        onaccent: token("onaccent"),
        // Status: severity always ships with an icon + label
        high: token("high"),
        med: token("med"),
        low: token("low"),
        good: token("good"),
        // Data colours: categorical slots 1-3, diverging red pole, item categories
        s1: token("s1"),
        s2: token("s2"),
        s3: token("s3"),
        neg: token("neg"),
        cw: token("cw"),
        cv: token("cv"),
        cs: token("cs"),
      },
    },
  },
  plugins: [],
};
