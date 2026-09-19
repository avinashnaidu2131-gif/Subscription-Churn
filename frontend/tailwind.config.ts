import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        obsidian: {
          DEFAULT: "#070A11",
          50: "#1A2234",
          100: "#141A29",
          200: "#0F1420",
          300: "#0B0F19",
          400: "#070A11",
        },
        surface: {
          DEFAULT: "rgba(15, 23, 42, 0.65)",
          hover: "rgba(30, 41, 59, 0.75)",
          active: "rgba(51, 65, 85, 0.75)",
        },
        cyan: {
          electric: "#06B6D4",
          glow: "rgba(6, 182, 212, 0.25)",
        },
        emerald: {
          recovery: "#10B981",
          glow: "rgba(16, 185, 129, 0.25)",
        },
        danger: {
          DEFAULT: "#F43F5E",
          glow: "rgba(244, 63, 94, 0.25)",
        },
      },
      animation: {
        "spin-slow": "spin 8s linear infinite",
        "pulse-fast": "pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-left": "slideLeft 0.35s cubic-bezier(0.16, 1, 0.3, 1)",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideLeft: {
          "0%": { transform: "translateX(100%)" },
          "100%": { transform: "translateX(0)" },
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "SF Mono", "Fira Code", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;

