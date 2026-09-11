/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        graphite: {
          950: "#121417",
          900: "#191C20",
          800: "#22262B",
          700: "#2C3136",
          600: "#3A3F45",
        },
        paper: {
          100: "#F3F1EC",
          200: "#EDEAE3",
          400: "#B7B3AA",
          600: "#8B877E",
        },
        moss: {
          400: "#5C9C86",
          500: "#3E6259",
          600: "#31504A",
        },
        gold: {
          400: "#C6A15B",
          500: "#B08D57",
        },
      },
      fontFamily: {
        serif: ["IBM Plex Serif", "serif"],
        sans: ["IBM Plex Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
