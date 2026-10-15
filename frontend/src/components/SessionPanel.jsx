/*
This file is the sessions panel on the bottom left of the screen.
The user can start a new chat, open a saved chat, or delete one.
*/
import { History, MessageSquare, MessagesSquare, Plus, Trash2 } from "lucide-react";
import { deleteSession } from "../api.js";

function relativeTime(timestamp) {
  // make a short label like "5m ago", the same way as format_relative_time in session_store.py
  const seconds = Date.now() / 1000 - timestamp;
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 86400 * 7) return `${Math.floor(seconds / 86400)}d ago`;
  return new Date(timestamp * 1000).toLocaleDateString();
}

export default function SessionPanel({ sessions, activeSessionId, onNewChat, onResume, onChanged }) {
  // delete the session, then refresh the list
  const removeSession = async (id) => {
    await deleteSession(id);

    // go to a new chat if the deleted session is the one open now, so its old messages do not stay on screen
    if (id === activeSessionId) onNewChat();

    onChanged();
  };

  return (
    <div className="flex flex-col h-full gap-2">
      <div className="flex items-center gap-2 shrink-0">
        {/* show an icon chip, the title, and how many chats there are */}
        <span className="w-7 h-7 rounded-lg bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center">
          <History size={15} />
        </span>
        <span className="font-medium text-sm text-slate-800">Chat history</span>
        <span className="bg-slate-100 text-slate-600 rounded-full px-2 text-[11px]">{sessions.length}</span>
        <button
          onClick={onNewChat}
          className="ml-auto inline-flex items-center gap-1.5 rounded-md bg-teal-700 text-white px-2.5 py-1.5 text-xs hover:bg-teal-800"
        >
          <Plus size={14} /> New chat
        </button>
      </div>

      {/* show the saved sessions, or a message if there are none */}
      {sessions.length > 0 ? (
        <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-0.5">
          {sessions.map((sess) => {
            const isActive = sess.id === activeSessionId;
            return (
              <div
                key={sess.id}
                className={`group flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs ${
                  isActive ? "bg-teal-50" : "hover:bg-slate-50"
                }`}
              >
                {/* the open session is disabled and highlighted, the others can be opened */}
                <button
                  disabled={isActive}
                  onClick={() => onResume(sess.id)}
                  className="flex-1 min-w-0 flex items-center gap-2 text-left"
                >
                  <MessageSquare size={14} className={`shrink-0 ${isActive ? "text-teal-700" : "text-slate-400"}`} />
                  <span className="min-w-0">
                    <span className={`block truncate ${isActive ? "font-medium text-teal-700" : "text-slate-700"}`}>
                      {sess.title}
                    </span>
                    <span className="block text-[11px] text-slate-400">
                      {sess.turn_count} turn(s), {relativeTime(sess.updated_at)}
                    </span>
                  </span>
                </button>
                <button
                  onClick={() => removeSession(sess.id)}
                  title="delete this session"
                  aria-label="delete this session"
                  className="p-1 rounded text-slate-300 hover:text-red-600 hover:bg-red-50 group-hover:text-slate-400"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center gap-1 text-center text-slate-400">
          <MessagesSquare size={24} strokeWidth={1.5} />
          <div className="text-xs font-medium text-slate-500">No saved sessions yet</div>
          <div className="text-[11px]">ask a question to start one</div>
        </div>
      )}
    </div>
  );
}
