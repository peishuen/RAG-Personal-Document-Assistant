// *** api client: thin fetch wrappers for every fastapi endpoint the ui calls ***
const BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "http://localhost:8000/api" : "/api");

export const getToken = () => localStorage.getItem("querio_access_token") || "";
export const setToken = (token) => localStorage.setItem("querio_access_token", token);
export const clearToken = () => localStorage.removeItem("querio_access_token");

const authHeaders = (extra = {}) => {
  const token = getToken();
  return token ? { "X-Access-Token": token, ...extra } : { ...extra };
};

export const verifyAuth = (token) => {
  const t = token !== undefined ? token : getToken();
  const headers = t ? { "X-Access-Token": t } : {};
  return fetch(`${BASE}/auth/verify`, { headers })
    .then((r) => r.json())
    .catch(() => ({ authenticated: false, auth_required: true }));
};

export const getDocuments = () =>
  fetch(`${BASE}/documents`, { headers: authHeaders() }).then((r) => r.json());

export const uploadDocuments = (files) => {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  return fetch(`${BASE}/documents`, { method: "POST", headers: authHeaders(), body: form }).then((r) => r.json());
};

export const deleteDocument = (source) =>
  fetch(`${BASE}/documents/${source}`, { method: "DELETE", headers: authHeaders() });

export const getSessions = () =>
  fetch(`${BASE}/sessions`, { headers: authHeaders() }).then((r) => r.json());

export const createSession = () =>
  fetch(`${BASE}/sessions`, { method: "POST", headers: authHeaders() }).then((r) => r.json());

export const getSession = (id) =>
  fetch(`${BASE}/sessions/${id}`, { headers: authHeaders() }).then((r) => r.json());

export const deleteSession = (id) =>
  fetch(`${BASE}/sessions/${id}`, { method: "DELETE", headers: authHeaders() });

export const askQuestion = (sessionId, question, sources) =>
  fetch(`${BASE}/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question, sources }),
  }).then((r) => r.json());
