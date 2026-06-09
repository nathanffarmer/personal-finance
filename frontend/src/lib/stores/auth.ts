import { writable } from "svelte/store";
import { browser } from "$app/environment";
import { getAppPassword, setAppPassword } from "$api/client";

const initial = browser ? (getAppPassword() ?? "") : "";

export const appPassword = writable(initial);

appPassword.subscribe((value) => {
  if (!browser) return;
  setAppPassword(value || null);
});
