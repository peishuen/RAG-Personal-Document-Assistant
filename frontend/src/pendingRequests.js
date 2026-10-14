/*
This file remembers which question is still waiting for an answer in each session.
If the user switches to another session and comes back, the question still
shows as pending instead of disappearing.
*/

// store the pending question for each session id
const pendingBySession = new Map();

// save, remove and read the pending question of a session
export const markPending = (sessionId, question) => pendingBySession.set(sessionId, question);
export const clearPending = (sessionId) => pendingBySession.delete(sessionId);
export const getPending = (sessionId) => pendingBySession.get(sessionId);
