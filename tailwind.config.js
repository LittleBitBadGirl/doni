/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        doni: {
          green: "#1e4d3d",
          "green-dark": "#0c2920",
          "green-light": "#2f6b56",
          sand: "#ece6d9",
          parchment: "#f9f6ef",
          cream: "#fffdf8",
          bark: "#3d3228",
          "bark-light": "#6b5d4f",
          gold: "#b8922f",
          "gold-light": "#d4b85a",
          "gold-dark": "#8a6b1e",
          mist: "#dfe8e3",
          amber: "#c4781a",
        },
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', "Georgia", "serif"],
        sans: ["Onest", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(12, 41, 32, 0.04), 0 8px 32px rgba(12, 41, 32, 0.07)",
        "card-hover":
          "0 2px 8px rgba(12, 41, 32, 0.06), 0 20px 48px rgba(12, 41, 32, 0.11)",
        header: "0 8px 32px rgba(12, 41, 32, 0.28)",
        inset: "inset 0 1px 0 rgba(255, 255, 255, 0.6)",
      },
      animation: {
        "fade-up": "fadeUp 0.8s cubic-bezier(0.22, 1, 0.36, 1) both",
        "fade-in": "fadeIn 0.6s ease-out both",
        "slide-in": "slideIn 0.7s cubic-bezier(0.22, 1, 0.36, 1) both",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideIn: {
          "0%": { opacity: "0", transform: "translateX(-12px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
      },
      backgroundImage: {
        grain:
          "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E\")",
        linen:
          "url(\"data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%230c2920' fill-opacity='0.025' fill-rule='evenodd'%3E%3Cpath d='M0 40L40 0H20L0 20M40 40V20L20 40'/%3E%3C/g%3E%3C/svg%3E\")",
        "hero-mesh":
          "radial-gradient(ellipse 90% 70% at 85% 5%, rgba(47, 107, 86, 0.12), transparent 55%), radial-gradient(ellipse 70% 60% at 5% 95%, rgba(184, 146, 47, 0.07), transparent 50%), radial-gradient(ellipse 50% 40% at 50% 50%, rgba(236, 230, 217, 0.5), transparent)",
        "gold-line":
          "linear-gradient(90deg, transparent, rgba(184, 146, 47, 0.45) 20%, rgba(184, 146, 47, 0.45) 80%, transparent)",
      },
    },
  },
  plugins: [],
};
