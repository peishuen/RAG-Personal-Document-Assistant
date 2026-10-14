/*
This file is the main shell of the app.
It keeps the shared state (documents, sessions, chat turns), checks the access token,
and lays out the screen: documents and sessions on the left, chat on the right.
It also shows a login screen when the user is not allowed in.
*/
import { useEffect, useState } from "react";
import { FileSearch, Lock, KeyRound, AlertCircle, Loader2 } from "lucide-react";
import DocumentPanel from "./components/DocumentPanel.jsx";
import SessionPanel from "./components/SessionPanel.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import { createSession, getDocuments, getSession, getSessions, getToken, setToken, verifyAuth } from "./api.js";
import { getPending } from "./pendingRequests.js";

export default function App() {
  // track the login state: "loading", "authorized" or "unauthorized"
  const [authStatus, setAuthStatus] = useState("loading");
  const [inputKey, setInputKey] = useState("");
  const [authError, setAuthError] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);

  // keep the shared data used by the panels
  const [documents, setDocuments] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [turns, setTurns] = useState([]);

  // reload the lists from the backend
  const refreshDocuments = () => getDocuments().then(setDocuments);
  const refreshSessions = () => getSessions().then(setSessions);

  // load the data and start a new chat after login
  const initApp = () => {
    refreshDocuments();
    refreshSessions();
    createSession().then(({ id }) => setActiveSessionId(id));
  };

  useEffect(() => {
    // look for a magic link token in the url (?access_token=... or ?token=... or ?key=...)
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("access_token") || params.get("token") || params.get("key");
    // use the url token first, then the saved token
    const tokenToTest = urlToken || getToken();

    verifyAuth(tokenToTest).then((res) => {
      if (res.authenticated) {
        if (urlToken) {
          // save the token and hide it from the address bar, without reloading the page
          setToken(urlToken);
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

  // check the access key typed in the login form
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

  // clear the chat and start a new session
  const startNewChat = () => {
    setTurns([]);
    createSession().then(({ id }) => setActiveSessionId(id));
  };

  // open a saved session and show its turns
  const resumeSession = (id) => {
    getSession(id).then((data) => {
      // add the question that is still waiting for an answer, if any
      const pendingQuestion = getPending(id);
      setTurns(pendingQuestion ? [...data.turns, { question: pendingQuestion, pending: true }] : data.turns);
      setActiveSessionId(id);
    });
  };

  // show a loading screen while the token is being checked
  if (authStatus === "loading") {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50 text-slate-600">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="animate-spin text-teal-700" size={28} />
          <span className="text-sm font-medium tracking-tight">Verifying access...</span>
        </div>
      </div>
    );
  }

  // show the login screen when the token is missing or wrong
  if (authStatus === "unauthorized") {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-100 p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 p-8 flex flex-col items-center text-center">
          <div className="w-14 h-14 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center mb-4 border border-teal-100">
            <Lock size={28} strokeWidth={1.5} />
          </div>
          <h1 className="text-xl font-medium text-slate-800 tracking-tight">Private project</h1>
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
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-600 focus:bg-white transition"
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
              className="w-full py-2.5 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl text-sm transition flex items-center justify-center gap-2"
            >
              {isVerifying && <Loader2 className="animate-spin" size={16} />}
              <span>Unlock assistant</span>
            </button>
          </form>
        </div>
      </div>
    );
  }

  // show the main screen
  return (
    <div className="h-screen overflow-hidden flex flex-col bg-slate-50 text-sm text-slate-800">
      {/* top bar with the logo and a short tagline */}
      <header className="shrink-0 bg-white border-b border-slate-200 px-4 py-2.5 flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-teal-700 text-white flex items-center justify-center">
          <FileSearch size={16} />
        </div>
        <span className="text-[15px] font-medium tracking-tight">Querio</span>
        <span className="hidden sm:inline text-slate-500 ml-1">Ask questions about your documents</span>
      </header>
      <div className="flex flex-1 overflow-hidden">
        {/* left column: documents and sessions are two cards, each takes half of the height */}
        <div className="w-2/5 flex flex-col gap-3 overflow-hidden bg-white border-r border-slate-200 p-3">
          <div className="flex-1 min-h-0 border border-slate-200 rounded-xl p-3">
            <DocumentPanel
              documents={documents}
              selectedSources={selectedSources}
              setSelectedSources={setSelectedSources}
              onChanged={refreshDocuments}
            />
          </div>
          <div className="flex-1 min-h-0 border border-slate-200 rounded-xl p-3">
            <SessionPanel
              sessions={sessions}
              activeSessionId={activeSessionId}
              onNewChat={startNewChat}
              onResume={resumeSession}
              onChanged={refreshSessions}
            />
          </div>
        </div>
        {/* right column: the chat */}
        <div className="w-3/5 flex flex-col overflow-hidden p-4">
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
