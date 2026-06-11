<script lang="ts">
  import { QueryClient, QueryClientProvider } from "@tanstack/svelte-query";
  import { page } from "$app/stores";
  import "../app.css";

  let { children } = $props();

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
    },
  });

  const nav = [
    { href: "/", label: "Dashboard" },
    { href: "/transactions", label: "Transactions" },
    { href: "/retirement", label: "Retirement" },
    { href: "/sheets", label: "Sheets" },
    { href: "/settings", label: "Settings" },
  ];

  let path = $derived($page.url.pathname);
  function isActive(href: string) {
    return href === "/" ? path === "/" : path.startsWith(href);
  }
</script>

<QueryClientProvider client={queryClient}>
  <div class="min-h-screen flex">
    <aside class="w-56 border-r border-slate-200 bg-white p-4">
      <h1 class="text-lg font-semibold mb-6">Personal Finance</h1>
      <nav class="flex flex-col gap-1">
        {#each nav as item}
          <a
            href={item.href}
            class="px-3 py-2 rounded text-sm {isActive(item.href)
              ? 'bg-ink text-white'
              : 'hover:bg-slate-100'}"
          >
            {item.label}
          </a>
        {/each}
      </nav>
    </aside>
    <main class="flex-1 p-6 overflow-auto">
      {@render children?.()}
    </main>
  </div>
</QueryClientProvider>
