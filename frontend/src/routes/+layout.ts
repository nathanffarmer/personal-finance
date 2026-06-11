// SPA mode — the FastAPI backend serves /api/*; SvelteKit does no SSR.
export const ssr = false;
export const prerender = false;
export const trailingSlash = "ignore";
