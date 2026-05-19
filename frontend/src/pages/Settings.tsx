import { useState } from "react";
import { getAppPassword, setAppPassword } from "@/api/client";

export default function Settings() {
  const [pwd, setPwd] = useState(getAppPassword() ?? "");
  const [saved, setSaved] = useState(false);

  return (
    <div className="max-w-lg">
      <h2 className="text-2xl font-semibold mb-4">Settings</h2>
      <div className="rounded border border-slate-200 bg-white p-4">
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
      </div>
      <p className="mt-6 text-sm text-slate-500">
        Monarch + Google OAuth status come online in later milestones.
      </p>
    </div>
  );
}
