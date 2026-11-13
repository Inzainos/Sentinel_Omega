/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Cyberpunk Terminal Palette
        bg: {
          deep: "#050607",
          panel: "#0b0c0d",
          card: "#111214",
        },
        fg: {
          primary: "#f0f4f8",
          secondary: "#a0a8b8",
          muted: "#6b7280",
          inverted: "#050607",
        },
        border: {
          DEFAULT: "rgba(255, 255, 255, 0.06)",
          dim: "rgba(255, 255, 255, 0.06)",
          glow: "rgba(0, 212, 255, 0.15)",
        },
        foreground: "#f0f4f8",
        muted: "#a0a8b8",
        faint: "#6b7280",
        body: "#f0f4f8",
        meta: "#a0a8b8",
        
        accent: {
          cyan: "#4db8ff",
          "cyan-dim": "rgba(77, 184, 255, 0.12)",
          violet: "#9b8cff",
          "violet-dim": "rgba(155, 140, 255, 0.12)",
          magenta: "#e0a7f4",
          "magenta-dim": "rgba(224, 167, 244, 0.12)",
        },
        risk: {
          low: "#10b981",
          "low-dim": "rgba(16, 185, 129, 0.12)",
          mid: "#ffc107",
          "mid-dim": "rgba(255, 193, 7, 0.12)",
          high: "#ff9100",
          "high-dim": "rgba(255, 145, 0, 0.12)",
          critical: "#ff1744",
          "critical-dim": "rgba(255, 23, 68, 0.12)",
        },
        success: "#10b981",
        warning: "#ffc107",
        danger: "#ff1744",
        info: "#00d4ff",

        // Legacy aliases for compatibility
        surface: {
          DEFAULT: "#111214",
          raised: "#15181b",
          sunken: "#0b0c0d",
        },
        "texto-principal": "#f0f4f8",
        "texto-secundario": "#a0a8b8",
        "texto-desvanecido": "#6b7280",
        "texto-calma": "#10b981",
        "texto-critico": "#ff1744",
        "texto-aviso": "#ff9100",
        "texto-atencion": "#ffc107",
        "borde": "rgba(255,255,255,0.06)",
        "bordeHover": "rgba(0,212,255,0.15)",
        sistema: {
          oscuro: "#050607",
          superficie: "#111214",
          "superficie-sunido": "#0b0c0d",
          texto: "#f0f4f8",
          desvanecido: "#6b7280",
          desvanecido2: "#6b7280",
        },
        acento: {
          DEFAULT: "#9b8cff",
          claro: "#4db8ff",
          oscuro: "#5b21b6",
        },
        riesgo: {
          calma: "#10b981",
          atencion: "#ffc107",
          alto: "#ff9100",
          critico: "#ff1744",
        },
      },
      fontFamily: {
        sans: ["Space Grotesk", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "ui-monospace", "monospace"],
        display: ["Orbitron", "Space Grotesk", "sans-serif"],
      },
      fontSize: {
        micro: ["0.7rem", { lineHeight: "1.4" }],
        pequeno: ["0.875rem", { lineHeight: "1.6" }],
        base: ["1rem", { lineHeight: "1.6" }],
        lg: ["1.125rem", { lineHeight: "1.6" }],
        xl: ["1.25rem", { lineHeight: "1.5" }],
        "2xl": ["1.5rem", { lineHeight: "1.3" }],
        "3xl": ["1.875rem", { lineHeight: "1.3" }],
        "4xl": ["2.25rem", { lineHeight: "1.3" }],
        gigante: ["3rem", { lineHeight: "1.2" }],
      },
      fontWeight: {
        regular: "400",
        medio: "500",
        negrita: "600",
        negro: "700",
      },
      borderRadius: {
        sm: "0.25rem",
        DEFAULT: "0.5rem",
        md: "0.75rem",
        lg: "1rem",
        xl: "1.25rem",
        "2xl": "1.5rem",
        "3xl": "1.875rem",
        completo: "9999px",
      },
      boxShadow: {
        "glow-cyan": "0 0 20px rgba(0, 212, 255, 0.3), 0 0 40px rgba(0, 212, 255, 0.1)",
        "glow-violet": "0 0 20px rgba(124, 77, 255, 0.3), 0 0 40px rgba(124, 77, 255, 0.1)",
        "glow-critical": "0 0 20px rgba(255, 23, 68, 0.3), 0 0 40px rgba(255, 23, 68, 0.1)",
        elevated: "0 8px 32px rgba(0, 0, 0, 0.4), 0 2px 8px rgba(0, 0, 0, 0.3)",
        card: "0 2px 12px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.03)",
      },
      transitionDuration: {
        fast: "120ms",
        base: "200ms",
        slow: "350ms",
      },
      transitionTimingFunction: {
        DEFAULT: "cubic-bezier(0.4, 0, 0.2, 1)",
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
  ],
}