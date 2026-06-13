/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        doni: {
          green: "#2d6a4f",
          "green-dark": "#1b4332",
          "green-light": "#40916c",
          sand: "#f4f1de",
          parchment: "#faf7f0",
          cream: "#faf7f0",
          bark: "#5c4a3d",
          gold: "#c9a227",
          "gold-dark": "#a67c00",
          mist: "#e8f0eb",
        },
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["Newsreader", "Georgia", "serif"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(27, 67, 50, 0.06), 0 8px 24px rgba(27, 67, 50, 0.08)",
        "card-hover": "0 4px 12px rgba(27, 67, 50, 0.1), 0 16px 40px rgba(27, 67, 50, 0.12)",
        header: "0 4px 24px rgba(27, 67, 50, 0.18)",
      },
      animation: {
        "fade-up": "fadeUp 0.7s ease-out both",
        "fade-in": "fadeIn 0.5s ease-out both",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
      backgroundImage: {
        grain:
          "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E\")",
        "hero-mesh":
          "radial-gradient(ellipse 80% 60% at 70% 20%, rgba(64, 145, 108, 0.15), transparent), radial-gradient(ellipse 60% 50% at 10% 80%, rgba(201, 162, 39, 0.08), transparent)",
        "gold-line":
          "linear-gradient(90deg, transparent, rgba(201, 162, 39, 0.4) 20%, rgba(201, 162, 39, 0.4) 80%, transparent)",
      },
    },
  },
  plugins: [],
};
