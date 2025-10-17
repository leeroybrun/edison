import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./pages/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0F172A",
        "ink-muted": "#475569",
        accent: "#14B8A6",
        focus: "#6366F1",
        success: "#16A34A",
        warn: "#F59E0B",
        error: "#EF4444",
        info: "#0EA5E9"
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Sohne", "Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"]
      }
    }
  },
  plugins: [require("tailwindcss-animate")]
};

export default config;
