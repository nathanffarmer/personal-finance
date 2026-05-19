import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1220",
        paper: "#f7f8fa",
      },
    },
  },
  plugins: [],
} satisfies Config;
