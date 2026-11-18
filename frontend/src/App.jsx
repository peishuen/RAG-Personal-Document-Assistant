/*
This file is the main shell of the app.
It keeps the shared state (documents, sessions, chat turns), checks the invitation link,
and lays out the screen: documents and sessions on the left, chat on the right.
It shows an invite-only screen when the user did not come from a valid invitation link.
*/
import { useEffect, useState } from "react";
import { FileSearch, Lock, Loader2 } from "lucide-react";
import DocumentPanel from "./components/DocumentPanel.jsx";
import SessionPanel from "./components/SessionPanel.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import { clearInvite, createSession, getDocuments, getSession, getSessions, getInvite, setInvite, verifyInvite } from "./api.js";
import { getPending } from "./pendingRequests.js";

export default function App() {
  // track the access state: "loading", "authorized", "unauthorized" or "offline"
  const [authStatus, setAuthStatus] = useState("loading");

  // keep the shared data used by the panels
  const [documents, setDocuments] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [turns, setTurns] = useState([]);

  // reload the lists from the backend
  const refreshDocuments = () => getDocuments().then(setDocuments);
  const refreshSessions = () => getSessions().then(setSessions);

  // load the data and start a new chat once the invite is accepted
  const initApp = () => {
    refreshDocuments();
    refreshSessions();
    createSession().then(({ id }) => setActiveSessionId(id));
  };

  useEffect(() => {
    // look for the invite code in the url (?invite=...)
    const params = new URLSearchParams(window.location.search);
    const urlInvite = params.get("invite");
    // use the code from the link first, then the one saved on an earlier visit
    const inviteToTest = urlInvite || getInvite();

    // hide the code from the address bar, without reloading the page
    if (urlInvite) {
      params.delete("invite");
      const query = params.toString();
      const cleanUrl = window.location.pathname + (query ? `?${query}` : "") + window.location.hash;
      window.history.replaceState({}, document.title, cleanUrl);
    }

    verifyInvite(inviteToTest).then((res) => {
      if (res.authenticated) {
        // remember the code, so the next visit works without the link
        if (urlInvite) setInvite(urlInvite);
        setAuthStatus("authorized");
        initApp();
      } else if (res.offline) {
        // keep the code when the server cannot be reached, so it still works once the server is back
        if (urlInvite) setInvite(urlInvite);
        setAuthStatus("offline");
      } else {
        // forget a saved code that no longer works (for example after the invite was changed)
        clearInvite();
        setAuthStatus("unauthorized");
      }
    });
  }, []);

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

  // show a loading screen while the invitation link is being checked
  if (authStatus === "loading") {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50 text-slate-600">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="animate-spin text-teal-700" size={28} />
          <span className="text-sm font-medium tracking-tight">Checking your invitation...</span>
        </div>
      </div>
    );
  }

  // show the invite-only screen when there is no valid invitation link, or the server is down
  if (authStatus === "unauthorized" || authStatus === "offline") {
    const offline = authStatus === "offline";
    return (
      <div className="h-screen flex items-center justify-center bg-slate-100 p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-slate-200 p-8 flex flex-col items-center text-center">
          <div className="w-14 h-14 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center mb-4 border border-teal-100">
            <Lock size={28} strokeWidth={1.5} />
          </div>
          <h1 className="text-xl font-medium text-slate-800 tracking-tight">
            {offline ? "Server offline" : "Invite only"}
          </h1>
          <p className="text-sm text-slate-500 mt-2 leading-relaxed">
            {offline
              ? "The Querio server cannot be reached right now. Please try again later."
              : "Querio is private. Open it from the invitation link you were sent. If your link stopped working, ask the owner for a new one."}
          </p>
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
