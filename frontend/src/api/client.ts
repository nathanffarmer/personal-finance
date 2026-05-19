const APP_PASSWORD_KEY = "pf:app_password";

export function setAppPassword(value: string | null): void {
  if (value === null || value === "") {
    localStorage.removeItem(APP_PASSWORD_KEY);
  } else {
    localStorage.setItem(APP_PASSWORD_KEY, value);
  }
}

export function getAppPassword(): string | null {
  return localStorage.getItem(APP_PASSWORD_KEY);
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const pwd = getAppPassword();
  if (pwd) headers.set("X-App-Password", pwd);

  const response = await fetch(path, { ...init, headers });
  const text = await response.text();
  const body = text ? safeJson(text) : null;
  if (!response.ok) {
    throw new ApiError(response.status, body, `${response.status} ${path}`);
  }
  return body as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
