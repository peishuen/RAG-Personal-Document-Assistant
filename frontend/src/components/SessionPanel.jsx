// *** session panel: start a new chat, resume or delete a saved session ***
import { History, Plus, Trash2 } from "lucide-react";
import { deleteSession } from "../api.js";

function relativeTime(timestamp) {
  // mirrors session_store.format_relative_time, just computed client-side for display
  const seconds = Date.now() / 1000 - timestamp;
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 86400 * 7) return `${Math.floor(seconds / 86400)}d ago`;
  return new Date(timestamp * 1000).toLocaleDateString();
}

export default function SessionPanel({ sessions, activeSessionId, onNewChat, onResume, onChanged }) {
  const removeSession = async (id) => {
    await deleteSession(id);
    onChanged();
  };

  return (
    <div className="flex flex-col h-full gap-2">
      <div className="flex items-center gap-2 text-teal-700 shrink-0">
        <History size={18} />
        <span className="font-semibold text-base">Sessions</span>
      </div>
      <button
        onClick={onNewChat}
        className="shrink-0 flex items-center justify-center gap-1.5 rounded-lg bg-teal-600 text-white px-3 py-2.5 text-sm font-medium hover:bg-teal-700"
      >
        <Plus size={16} /> New chat
      </button>
      {sessions.length > 0 ? (
        <div className="flex-1 min-h-0 overflow-y-auto border border-teal-100 rounded-lg bg-teal-50/60 divide-y divide-teal-100">
          {sessions.map((sess) => (
            <div
              key={sess.id}
              className="flex items-center gap-2 px-3 py-2 text-xs hover:bg-white transition-colors"
            >
              <button
                disabled={sess.id === activeSessionId}
                onClick={() => onResume(sess.id)}
                className={`flex-1 text-left ${
                  sess.id === activeSessionId ? "text-teal-600 font-medium" : "text-slate-700"
                }`}
              >
                <span className="inline-flex items-center gap-1.5">
                  {sess.id === activeSessionId && <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />}
                  {sess.title}
                </span>
                <div className="text-slate-400">{sess.turn_count} turn(s) · {relativeTime(sess.updated_at)}</div>
              </button>
              <button
                onClick={() => removeSession(sess.id)}
                title="delete this session"
                className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-xs text-slate-400">no saved sessions yet, ask a question to start one</div>
      )}
    </div>
  );
}
