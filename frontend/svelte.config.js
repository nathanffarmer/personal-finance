import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    // SPA mode: backend lives elsewhere (FastAPI on :8000), no SSR needed.
    adapter: adapter({ fallback: "index.html" }),
    alias: {
      $components: "src/lib/components",
      $api: "src/lib/api",
      $stores: "src/lib/stores",
    },
  },
};

export default config;
