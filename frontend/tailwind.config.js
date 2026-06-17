/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0066cc",
          50: "#e6f0fa",
          100: "#cce0f5",
          700: "#004d99",
        },
      },
    },
  },
  plugins: [],
};
