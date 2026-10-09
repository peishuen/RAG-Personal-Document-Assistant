// *** api client: thin fetch wrappers for every fastapi endpoint the ui calls ***
const BASE = "http://localhost:8000/api";

export const getDocuments = () => fetch(`${BASE}/documents`).then((r) => r.json());

export const uploadDocuments = (files) => {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  return fetch(`${BASE}/documents`, { method: "POST", body: form }).then((r) => r.json());
};

export const deleteDocument = (source) =>
  fetch(`${BASE}/documents/${source}`, { method: "DELETE" });

export const getSessions = () => fetch(`${BASE}/sessions`).then((r) => r.json());

export const createSession = () => fetch(`${BASE}/sessions`, { method: "POST" }).then((r) => r.json());

export const getSession = (id) => fetch(`${BASE}/sessions/${id}`).then((r) => r.json());

export const deleteSession = (id) => fetch(`${BASE}/sessions/${id}`, { method: "DELETE" });

export const askQuestion = (sessionId, question, sources) =>
  fetch(`${BASE}/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, sources }),
  }).then((r) => r.json());
