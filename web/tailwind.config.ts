import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        heading: ["Newsreader", "Georgia", "serif"],
        body: ["Outfit", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        glass: "0 18px 45px rgba(13, 55, 68, 0.18)",
      },
    },
  },
  plugins: [],
} satisfies Config;
