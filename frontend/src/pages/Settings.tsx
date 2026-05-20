import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getAppPassword, setAppPassword } from "@/api/client";
import { monarchApi } from "@/api/monarch";
import { sheetsApi } from "@/api/sheets";

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${
        ok ? "bg-emerald-500" : "bg-slate-300"
      }`}
    />
  );
}

export default function Settings() {
  const qc = useQueryClient();
  const [pwd, setPwd] = useState(getAppPassword() ?? "");
  const [saved, setSaved] = useState(false);

  const monarch = useQuery({
    queryKey: ["monarch", "status"],
    queryFn: monarchApi.status,
  });
  const sheets = useQuery({
    queryKey: ["sheets", "status"],
    queryFn: sheetsApi.status,
  });

  const clearCache = async () => {
    await monarchApi.clearCache();
    await qc.invalidateQueries();
  };

  return (
    <div className="max-w-2xl space-y-6">
      <h2 className="text-2xl font-semibold">Settings</h2>

      <section className="rounded border border-slate-200 bg-white p-4">
        <label htmlFor="app-password" className="block text-sm font-medium mb-2">
          App password
        </label>
        <p className="text-xs text-slate-500 mb-3">
          Must match <code>APP_PASSWORD</code> in your backend .env. Leave blank if auth is
          disabled (localhost dev).
        </p>
        <input
          id="app-password"
          type="password"
          value={pwd}
          onChange={(e) => {
            setPwd(e.target.value);
            setSaved(false);
          }}
          className="w-full border border-slate-300 rounded px-3 py-2 text-sm"
        />
        <button
          className="mt-3 px-3 py-2 bg-ink text-white text-sm rounded"
          onClick={() => {
            setAppPassword(pwd || null);
            setSaved(true);
          }}
        >
          Save
        </button>
        {saved && <span className="ml-3 text-sm text-emerald-600">Saved.</span>}
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-3">Monarch Money</h3>
        {monarch.isLoading && <div className="text-sm text-slate-500">Checking…</div>}
        {monarch.error && (
          <div className="text-sm text-amber-700">Could not reach backend.</div>
        )}
        {monarch.data && (
          <ul className="text-sm space-y-1">
            <li className="flex items-center gap-2">
              <StatusDot ok={monarch.data.credentials_configured} />
              Credentials configured (MONARCH_EMAIL / MONARCH_PASSWORD)
            </li>
            <li className="flex items-center gap-2">
              <StatusDot ok={monarch.data.mfa_secret_configured} />
              MFA secret configured
            </li>
            <li className="flex items-center gap-2">
              <StatusDot ok={monarch.data.session_cached} />
              Session cached
            </li>
            <li className="flex items-center gap-2">
              <StatusDot ok={monarch.data.logged_in} />
              Logged in this run
            </li>
          </ul>
        )}
        <p className="text-xs text-slate-400 mt-2">
          If no MFA secret is set, run <code>python scripts/monarch_login.py</code> once.
        </p>
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-3">Google Sheets</h3>
        {sheets.isLoading && <div className="text-sm text-slate-500">Checking…</div>}
        {sheets.data && (
          <ul className="text-sm space-y-1">
            <li className="flex items-center gap-2">
              <StatusDot ok={sheets.data.authorized} />
              OAuth authorized
            </li>
            <li className="flex items-center gap-2">
              <StatusDot ok={!!sheets.data.sheet_id} />
              Sheet ID set
              {sheets.data.sheet_id && (
                <span className="font-mono text-xs text-slate-400 break-all">
                  {sheets.data.sheet_id}
                </span>
              )}
            </li>
          </ul>
        )}
        {sheets.data?.error && (
          <p className="text-xs text-amber-700 mt-2">{sheets.data.error}</p>
        )}
        <p className="text-xs text-slate-400 mt-2">
          To authorize, run <code>python scripts/bootstrap_oauth.py</code> once.
        </p>
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-3">Cache</h3>
        <button
          onClick={clearCache}
          className="px-3 py-2 text-sm rounded border border-slate-300 hover:bg-slate-50"
        >
          Clear cache
        </button>
        <p className="text-xs text-slate-400 mt-2">
          Forces the next request to re-fetch live from Monarch.
        </p>
      </section>
    </div>
  );
}
