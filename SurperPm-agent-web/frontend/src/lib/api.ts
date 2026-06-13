const BASE = "/api";

function createApi() {
  async function request(method: string, path: string, body?: unknown) {
    const res = await fetch(`${BASE}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (res.status === 401) {
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
      throw new Error("unauthorized");
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? `${res.status} ${res.statusText}`);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  return new Proxy({} as Record<string, Function>, {
    get(_, method: string) {
      return (path: string, body?: unknown) => request(method.toUpperCase(), path, body);
    },
  });
}

export const api = createApi() as {
  get: <T = unknown>(path: string) => Promise<T>;
  post: <T = unknown>(path: string, body?: unknown) => Promise<T>;
  patch: <T = unknown>(path: string, body?: unknown) => Promise<T>;
  put: <T = unknown>(path: string, body?: unknown) => Promise<T>;
  delete: (path: string) => Promise<null>;
};
