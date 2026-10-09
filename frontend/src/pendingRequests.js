// *** tracks the question still being answered per session, so switching away and back shows it as pending instead of missing ***
const pendingBySession = new Map();

export const markPending = (sessionId, question) => pendingBySession.set(sessionId, question);
export const clearPending = (sessionId) => pendingBySession.delete(sessionId);
export const getPending = (sessionId) => pendingBySession.get(sessionId);
