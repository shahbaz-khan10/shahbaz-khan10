import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          500: "#2f6fed",
          600: "#1f5ad0",
          700: "#1a4aac",
          800: "#173d8d",
          900: "#163470",
        },
      },
    },
  },
  plugins: [],
};

export default config;