// *** app shell: holds shared state, verifies access token, and lays out the two-pane screen ***
import { useEffect, useState } from "react";
import { Sparkles, Lock, KeyRound, AlertCircle, Loader2 } from "lucide-react";
import DocumentPanel from "./components/DocumentPanel.jsx";
import SessionPanel from "./components/SessionPanel.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import { createSession, getDocuments, getSession, getSessions, getToken, setToken, verifyAuth } from "./api.js";
import { getPending } from "./pendingRequests.js";

export default function App() {
  const [authStatus, setAuthStatus] = useState("loading"); // "loading" | "authorized" | "unauthorized"
  const [inputKey, setInputKey] = useState("");
  const [authError, setAuthError] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);

  const [documents, setDocuments] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [turns, setTurns] = useState([]);

  const refreshDocuments = () => getDocuments().then(setDocuments);
  const refreshSessions = () => getSessions().then(setSessions);

  const initApp = () => {
    refreshDocuments();
    refreshSessions();
    createSession().then(({ id }) => setActiveSessionId(id));
  };

  useEffect(() => {
    // Check if magic link parameter exists in URL (?access_token=... or ?token=... or ?key=...)
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("access_token") || params.get("token") || params.get("key");
    const tokenToTest = urlToken || getToken();

    verifyAuth(tokenToTest).then((res) => {
      if (res.authenticated) {
        if (urlToken) {
          setToken(urlToken);
          // Remove token from address bar for clean display without reloading
          const cleanUrl = window.location.pathname + window.location.hash;
          window.history.replaceState({}, document.title, cleanUrl);
        }
        setAuthStatus("authorized");
        initApp();
      } else {
        setAuthStatus("unauthorized");
      }
    });
  }, []);

  const handleManualUnlock = (e) => {
    e.preventDefault();
    if (!inputKey.trim()) return;

    setIsVerifying(true);
    setAuthError("");

    verifyAuth(inputKey.trim()).then((res) => {
      setIsVerifying(false);
      if (res.authenticated) {
        setToken(inputKey.trim());
        setAuthStatus("authorized");
        initApp();
      } else {
        setAuthError("Invalid access key. Please check and try again.");
      }
    }).catch(() => {
      setIsVerifying(false);
      setAuthError("Failed to verify access key. Please try again.");
    });
  };

  const startNewChat = () => {
    setTurns([]);
    createSession().then(({ id }) => setActiveSessionId(id));
  };

  const resumeSession = (id) => {
    getSession(id).then((data) => {
      const pendingQuestion = getPending(id);
      setTurns(pendingQuestion ? [...data.turns, { question: pendingQuestion, pending: true }] : data.turns);
      setActiveSessionId(id);
    });
  };

  if (authStatus === "loading") {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50 text-slate-600">
        <div className="flex flex-col items-center gap-3">
          <Sparkles className="animate-spin text-teal-600" size={28} />
          <span className="text-sm font-medium tracking-tight">Verifying access...</span>
        </div>
      </div>
    );
  }

  if (authStatus === "unauthorized") {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-100 p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 p-8 flex flex-col items-center text-center">
          <div className="w-14 h-14 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center mb-4 border border-teal-100">
            <Lock size={28} />
          </div>
          <h1 className="text-xl font-bold text-slate-800 tracking-tight">Private Project</h1>
          <p className="text-sm text-slate-500 mt-2 leading-relaxed">
            This document assistant is restricted. Access requires an authorized magic link or access key.
          </p>

          <form onSubmit={handleManualUnlock} className="w-full mt-6 space-y-3">
            <div className="relative">
              <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="password"
                placeholder="Enter access key..."
                value={inputKey}
                onChange={(e) => setInputKey(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white transition"
              />
            </div>
            {authError && (
              <div className="flex items-center gap-1.5 text-xs text-rose-600 font-medium text-left">
                <AlertCircle size={14} className="shrink-0" />
                <span>{authError}</span>
              </div>
            )}
            <button
              type="submit"
              disabled={isVerifying || !inputKey.trim()}
              className="w-full py-2.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl text-sm transition flex items-center justify-center gap-2 shadow-sm"
            >
              {isVerifying && <Loader2 className="animate-spin" size={16} />}
              <span>Unlock Assistant</span>
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen overflow-hidden flex flex-col bg-slate-50 text-sm text-slate-800">
      <div className="shrink-0 bg-teal-600 text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={20} />
          <span className="text-lg font-bold tracking-tight">Querio</span>
        </div>
      </div>
      <div className="flex flex-1 overflow-hidden">
        {/* left column: documents and sessions each get exactly half the column's height */}
        <div className="w-2/5 flex flex-col overflow-hidden bg-white border-r border-slate-200">
          <div className="flex-1 min-h-0 p-3">
            <DocumentPanel
              documents={documents}
              selectedSources={selectedSources}
              setSelectedSources={setSelectedSources}
              onChanged={refreshDocuments}
            />
          </div>
          <div className="shrink-0 border-t border-slate-200" />
          <div className="flex-1 min-h-0 p-3">
            <SessionPanel
              sessions={sessions}
              activeSessionId={activeSessionId}
              onNewChat={startNewChat}
              onResume={resumeSession}
              onChanged={refreshSessions}
            />
          </div>
        </div>
        <div className="w-3/5 flex flex-col overflow-hidden p-3">
          <ChatPanel
            hasDocuments={documents.length > 0}
            sessionId={activeSessionId}
            selectedSources={selectedSources}
            turns={turns}
            setTurns={setTurns}
            onAnswered={refreshSessions}
          />
        </div>
      </div>
    </div>
  );
}
