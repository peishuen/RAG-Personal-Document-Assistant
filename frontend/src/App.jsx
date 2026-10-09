// *** app shell: holds shared state and lays out the two-pane document/chat screen ***
import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import DocumentPanel from "./components/DocumentPanel.jsx";
import SessionPanel from "./components/SessionPanel.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import { createSession, getDocuments, getSession, getSessions } from "./api.js";
import { getPending } from "./pendingRequests.js";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [turns, setTurns] = useState([]);

  const refreshDocuments = () => getDocuments().then(setDocuments);
  const refreshSessions = () => getSessions().then(setSessions);

  useEffect(() => {
    refreshDocuments();
    refreshSessions();
    createSession().then(({ id }) => setActiveSessionId(id));
  }, []);

  const startNewChat = () => {
    setTurns([]);
    createSession().then(({ id }) => setActiveSessionId(id));
  };

  const resumeSession = (id) => {
    getSession(id).then((data) => {
      // a question asked just before switching away may still be in flight, show it as
      // pending rather than missing, it'll be replaced with the real answer once ask()
      // in ChatPanel sees this session is active again, or on the next resume otherwise
      const pendingQuestion = getPending(id);
      setTurns(pendingQuestion ? [...data.turns, { question: pendingQuestion, pending: true }] : data.turns);
      setActiveSessionId(id);
    });
  };

  return (
    <div className="h-screen overflow-hidden flex flex-col bg-slate-50 text-sm text-slate-800">
      <div className="shrink-0 bg-teal-600 text-white px-4 py-3 flex items-center gap-2">
        <Sparkles size={20} />
        <span className="text-lg font-bold tracking-tight">Querio</span>
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
