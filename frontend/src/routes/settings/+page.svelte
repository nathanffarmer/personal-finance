<script lang="ts">
  import { createQuery, useQueryClient } from "@tanstack/svelte-query";
  import { monarchApi } from "$api/monarch";
  import { sheetsApi } from "$api/sheets";
  import { appPassword } from "$stores/auth";

  const qc = useQueryClient();
  let pwd = $state($appPassword);
  let saved = $state(false);

  const monarch = createQuery({
    queryKey: ["monarch", "status"],
    queryFn: monarchApi.status,
  });
  const sheets = createQuery({
    queryKey: ["sheets", "status"],
    queryFn: sheetsApi.status,
  });

  async function clearCache() {
    await monarchApi.clearCache();
    await qc.invalidateQueries();
  }

  function save() {
    appPassword.set(pwd);
    saved = true;
  }
</script>

{#snippet dot(ok: boolean)}
  <span class="inline-block w-2.5 h-2.5 rounded-full {ok ? 'bg-emerald-500' : 'bg-slate-300'}"></span>
{/snippet}

<div class="max-w-2xl space-y-6">
  <h2 class="text-2xl font-semibold">Settings</h2>

  <section class="rounded border border-slate-200 bg-white p-4">
    <label for="app-password" class="block text-sm font-medium mb-2">App password</label>
    <p class="text-xs text-slate-500 mb-3">
      Must match <code>APP_PASSWORD</code> in your backend .env. Leave blank if auth is
      disabled (localhost dev).
    </p>
    <input
      id="app-password"
      type="password"
      bind:value={pwd}
      oninput={() => (saved = false)}
      class="w-full border border-slate-300 rounded px-3 py-2 text-sm"
    />
    <button class="mt-3 px-3 py-2 bg-ink text-white text-sm rounded" onclick={save}>
      Save
    </button>
    {#if saved}
      <span class="ml-3 text-sm text-emerald-600">Saved.</span>
    {/if}
  </section>

  <section class="rounded border border-slate-200 bg-white p-4">
    <h3 class="font-semibold mb-3">Monarch Money</h3>
    {#if $monarch.isLoading}
      <div class="text-sm text-slate-500">Checking…</div>
    {/if}
    {#if $monarch.error}
      <div class="text-sm text-amber-700">Could not reach backend.</div>
    {/if}
    {#if $monarch.data}
      <ul class="text-sm space-y-1">
        <li class="flex items-center gap-2">
          {@render dot($monarch.data.credentials_configured)}
          Credentials configured (MONARCH_EMAIL / MONARCH_PASSWORD)
        </li>
        <li class="flex items-center gap-2">
          {@render dot($monarch.data.mfa_secret_configured)}
          MFA secret configured
        </li>
        <li class="flex items-center gap-2">
          {@render dot($monarch.data.session_cached)}
          Session cached
        </li>
        <li class="flex items-center gap-2">
          {@render dot($monarch.data.logged_in)}
          Logged in this run
        </li>
      </ul>
    {/if}
    <p class="text-xs text-slate-400 mt-2">
      If no MFA secret is set, run <code>python scripts/monarch_login.py</code> once.
    </p>
  </section>

  <section class="rounded border border-slate-200 bg-white p-4">
    <h3 class="font-semibold mb-3">Google Sheets</h3>
    {#if $sheets.isLoading}
      <div class="text-sm text-slate-500">Checking…</div>
    {/if}
    {#if $sheets.data}
      <ul class="text-sm space-y-1">
        <li class="flex items-center gap-2">
          {@render dot($sheets.data.authorized)}
          OAuth authorized
        </li>
        <li class="flex items-center gap-2">
          {@render dot(!!$sheets.data.sheet_id)}
          Sheet ID set
          {#if $sheets.data.sheet_id}
            <span class="font-mono text-xs text-slate-400 break-all">
              {$sheets.data.sheet_id}
            </span>
          {/if}
        </li>
      </ul>
    {/if}
    {#if $sheets.data?.error}
      <p class="text-xs text-amber-700 mt-2">{$sheets.data.error}</p>
    {/if}
    <p class="text-xs text-slate-400 mt-2">
      To authorize, run <code>python scripts/bootstrap_oauth.py</code> once.
    </p>
  </section>

  <section class="rounded border border-slate-200 bg-white p-4">
    <h3 class="font-semibold mb-3">Cache</h3>
    <button
      onclick={clearCache}
      class="px-3 py-2 text-sm rounded border border-slate-300 hover:bg-slate-50"
    >
      Clear cache
    </button>
    <p class="text-xs text-slate-400 mt-2">
      Forces the next request to re-fetch live from Monarch.
    </p>
  </section>
</div>
