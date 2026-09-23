import { defineConfig } from "vite";
export default defineConfig({
  build: {
    rollupOptions: {
      input: { exchange: "index.html", research: "research.html" },
    },
  },
});
