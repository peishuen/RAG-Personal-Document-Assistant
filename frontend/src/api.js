/*
This file has small helper functions that call the fastapi backend.
Each function matches one api endpoint, such as documents, sessions or chat.
The components use these helpers, so they never call fetch directly.
*/

// pick the api address: env variable first, then localhost in dev, then /api in production
const BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "http://localhost:8000/api" : "/api");

// save, read and remove the access token in the browser
export const getToken = () => localStorage.getItem("querio_access_token") || "";
export const setToken = (token) => localStorage.setItem("querio_access_token", token);
export const clearToken = () => localStorage.removeItem("querio_access_token");

// build the request headers and add the access token if there is one
const authHeaders = (extra = {}) => {
  const token = getToken();
  return token ? { "X-Access-Token": token, ...extra } : { ...extra };
};

// ask the backend if the token is valid, and treat a network error as not authenticated
export const verifyAuth = (token) => {
  const t = token !== undefined ? token : getToken();
  const headers = t ? { "X-Access-Token": t } : {};
  return fetch(`${BASE}/auth/verify`, { headers })
    .then((r) => r.json())
    .catch(() => ({ authenticated: false, auth_required: true }));
};

// get the list of stored documents
export const getDocuments = () =>
  fetch(`${BASE}/documents`, { headers: authHeaders() }).then((r) => r.json());

// upload one or more files as form data
export const uploadDocuments = (files) => {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  return fetch(`${BASE}/documents`, { method: "POST", headers: authHeaders(), body: form }).then((r) => r.json());
};

// delete one document
export const deleteDocument = (source) =>
  fetch(`${BASE}/documents/${source}`, { method: "DELETE", headers: authHeaders() });

// get all saved sessions
export const getSessions = () =>
  fetch(`${BASE}/sessions`, { headers: authHeaders() }).then((r) => r.json());

// create a new empty session
export const createSession = () =>
  fetch(`${BASE}/sessions`, { method: "POST", headers: authHeaders() }).then((r) => r.json());

// get one session with its turns
export const getSession = (id) =>
  fetch(`${BASE}/sessions/${id}`, { headers: authHeaders() }).then((r) => r.json());

// delete one session
export const deleteSession = (id) =>
  fetch(`${BASE}/sessions/${id}`, { method: "DELETE", headers: authHeaders() });

// send a question and read the answer as it streams in, then return the finished turn
// onToken is called with each new piece of text, so the screen can show it at once
export const askQuestionStream = async (sessionId, question, sources, onToken) => {
  const response = await fetch(`${BASE}/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question, sources }),
  });
  if (!response.ok || !response.body) throw new Error("request failed");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalTurn = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // add the new bytes, then split out every complete event (each ends with a blank line)
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop();

    for (const raw of events) {
      if (!raw.startsWith("data: ")) continue;
      const event = JSON.parse(raw.slice(6));

      if (event.type === "token") onToken(event.text);
      else if (event.type === "done") finalTurn = event.turn;
      else if (event.type === "error") throw new Error(event.message);
    }
  }

  if (!finalTurn) throw new Error("the answer stream ended early");
  return finalTurn;
};

// send a question and get back the answer, with the chosen documents to search in
export const askQuestion = (sessionId, question, sources) =>
  fetch(`${BASE}/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question, sources }),
  }).then((r) => r.json());
