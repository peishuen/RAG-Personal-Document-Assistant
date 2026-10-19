/*
This file is the chat panel on the right side of the screen.
It shows the past questions and answers, suggested prompts for an empty chat,
and the input box. It sends new questions to the backend and shows the answer,
the source links, and the grounding result.
*/
import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUp,
  CheckCircle2,
  FileText,
  GitCompare,
  Lightbulb,
  ListChecks,
  Loader2,
  MessageCircle,
  Sparkles,
  Target,
} from "lucide-react";
import { askQuestionStream, getSession } from "../api.js";
import { clearPending, markPending } from "../pendingRequests.js";

// check for the grounding result every second, up to 10 times
// the check finishes a little after the answer, so we need to wait for it
const GROUNDING_POLL_MS = 1000;
const GROUNDING_MAX_ATTEMPTS = 10;

// list the suggestions shown in an empty chat, each with an icon
const SUGGESTED_PROMPTS = [
  { text: "Summarize the key points across all my documents", icon: ListChecks },
  { text: "What are the main findings?", icon: Target },
  { text: "Compare the documents I've uploaded", icon: GitCompare },
  { text: "Explain this in simple terms", icon: Lightbulb },
];

// turn "[Source 2]" or "[2]" in the answer into a small link to that source below
function renderAnswer(answer, turnIndex) {
  // split the text so the citation markers become separate pieces
  const pieces = answer.split(/(\[Source \d+\]|\[\d+\])/g);

  return pieces.map((piece, i) => {
    // keep normal text as it is
    const match = piece.match(/^\[(?:Source )?(\d+)\]$/);
    if (!match) return piece;

    const number = match[1];
    return (
      <a
        key={i}
        href={`#turn-${turnIndex}-source-${number}`}
        className="inline-flex items-center justify-center w-5 h-5 mx-0.5 rounded-full bg-teal-100 text-teal-800 text-[11px] font-medium align-middle hover:bg-teal-200"
        title={`Source ${number}`}
      >
        {number}
      </a>
    );
  });
}

export default function ChatPanel({ hasDocuments, sessionId, selectedSources, turns, setTurns, onAnswered }) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollBoxRef = useRef(null);

  // scroll to the newest message whenever the turns change
  useEffect(() => {
    const box = scrollBoxRef.current;
    if (box) box.scrollTop = box.scrollHeight;
  }, [turns]);

  // remember which session is open now
  // an answer can arrive after the user switched session, so we use this to ignore old answers
  const activeSessionIdRef = useRef(sessionId);
  useEffect(() => {
    activeSessionIdRef.current = sessionId;
    // allow typing again, because a request from another session should not block this one
    setSending(false);
  }, [sessionId]);

  // keep fetching the session until the grounding result is ready, then show it
  const pollForGrounding = (forSessionId, turnIndex, attempt = 0) => {
    // stop after too many tries
    if (attempt >= GROUNDING_MAX_ATTEMPTS) return;

    setTimeout(async () => {
      const data = await getSession(forSessionId);
      const updatedTurn = data.turns[turnIndex];

      if (updatedTurn && updatedTurn.grounded !== null) {
        // update the screen only if the user is still in the same session
        if (forSessionId === activeSessionIdRef.current) {
          setTurns((prev) => {
            const updated = [...prev];
            updated[turnIndex] = updatedTurn;
            return updated;
          });
        }
      } else {
        // try again if the result is not ready yet
        pollForGrounding(forSessionId, turnIndex, attempt + 1);
      }
    }, GROUNDING_POLL_MS);
  };

  // send a question to the backend and show the answer
  const ask = async (question) => {
    // do nothing if the question is empty or an answer is still loading
    if (!question || !sessionId || sending) return;
    const forSessionId = sessionId;
    setInput("");
    setSending(true);
    markPending(forSessionId, question);

    // show the question at once, and fill in the answer when it comes back
    let turnIndex;
    setTurns((prev) => {
      turnIndex = prev.length;
      return [...prev, { question, pending: true }];
    });

    // read the answer as it streams in, and show each new piece at once
    let turn;
    try {
      turn = await askQuestionStream(forSessionId, question, selectedSources, (text) => {
        // ignore pieces that arrive after the user switched session
        if (forSessionId !== activeSessionIdRef.current) return;
        setTurns((prev) => {
          const updated = [...prev];
          const current = updated[turnIndex];
          if (current && current.pending) {
            updated[turnIndex] = { ...current, streamText: (current.streamText || "") + text };
          }
          return updated;
        });
      });
    } catch (error) {
      // drop the waiting turn and unlock the input when the request fails
      clearPending(forSessionId);
      setSending(false);
      if (forSessionId === activeSessionIdRef.current) {
        setTurns((prev) => prev.filter((_, index) => index !== turnIndex));
      }
      return;
    }
    clearPending(forSessionId);
    setSending(false);
    onAnswered();

    // the backend already saved this turn, so update the screen only if the user is still in the same session
    if (forSessionId === activeSessionIdRef.current) {
      setTurns((prev) => {
        const updated = [...prev];
        updated[turnIndex] = turn;
        return updated;
      });

      // start checking for the grounding result, because the server is still working on it
      if (turn.grounded === null) {
        pollForGrounding(forSessionId, turnIndex);
      }
    }
  };

  // ask the user to upload a document first if there are none
  if (!hasDocuments) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center gap-2 text-slate-400">
        <MessageCircle size={28} strokeWidth={1.5} />
        <div className="font-medium text-base text-slate-600">Ask your documents</div>
        <div className="text-sm">upload at least one document before asking a question</div>
      </div>
    );
  }

  // show the chat box and the input
  return (
    <div className="flex flex-col h-full gap-3">
      <div ref={scrollBoxRef} className="flex-1 min-h-0 overflow-y-auto flex flex-col px-1">
        {/* show suggestions when the chat is empty, and show the turns otherwise */}
        {turns.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-5">
            {/* use a solid teal tile with a white icon, so it stands out on the light page */}
            <div className="w-12 h-12 rounded-2xl bg-teal-700 text-white flex items-center justify-center shadow-sm">
              <Sparkles size={22} />
            </div>
            <div>
              <h3 className="text-lg font-medium text-slate-800">What would you like to know?</h3>
              <p className="text-slate-500 text-sm">pick a suggestion or type your own question below</p>
            </div>
            <div className="grid grid-cols-2 gap-2 max-w-xl w-full">
              {SUGGESTED_PROMPTS.map(({ text, icon: Icon }) => (
                <button
                  key={text}
                  onClick={() => ask(text)}
                  className="flex items-start gap-2.5 text-left bg-white border border-slate-200 rounded-xl p-3 text-sm text-slate-600 hover:border-teal-300 hover:bg-teal-50/50 hover:text-teal-800 transition-colors"
                >
                  <Icon size={16} className="mt-0.5 shrink-0 text-teal-700" />
                  <span>{text}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="w-full max-w-3xl mx-auto">
            {turns.map((turn, i) => (
              <div key={i} className="flex flex-col gap-3 mb-6">
                {/* show the question as a bubble on the right */}
                <div className="self-end max-w-[80%] bg-slate-200 text-slate-800 rounded-2xl rounded-br-sm px-3.5 py-2 ml-auto w-fit">
                  {turn.question}
                </div>

                <div className="flex items-start gap-3">
                  <div className="shrink-0 w-6 h-6 rounded-full bg-teal-700 text-white flex items-center justify-center">
                    <Sparkles size={13} />
                  </div>

                  {/* show a loading bar while waiting, the streaming text as it arrives, then the full answer */}
                  {turn.pending && turn.streamText ? (
                    <div className="flex-1 min-w-0 text-slate-700 whitespace-pre-wrap leading-relaxed">
                      {renderAnswer(turn.streamText, i)}
                    </div>
                  ) : turn.pending ? (
                    <div className="flex-1 pt-2.5">
                      <div className="h-1.5 w-32 bg-teal-100 rounded-full loading-bar-track text-teal-500">
                        <div className="loading-bar-fill" />
                      </div>
                    </div>
                  ) : (
                    <div className="flex-1 min-w-0 text-slate-700">
                      <div className="whitespace-pre-wrap leading-relaxed">{renderAnswer(turn.answer, i)}</div>

                      <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                        {/* show the grounding result: checking, grounded, or not grounded */}
                        {turn.grounded === null ? (
                          <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                            <Loader2 size={12} className="animate-spin" /> checking groundedness...
                          </span>
                        ) : turn.grounded ? (
                          <span
                            title={turn.grounding_reason}
                            className="inline-flex items-center gap-1 text-xs text-emerald-800 bg-emerald-50 rounded-full px-2 py-0.5"
                          >
                            <CheckCircle2 size={12} /> Grounded
                          </span>
                        ) : (
                          <span
                            title={turn.grounding_reason}
                            className="inline-flex items-center gap-1 text-xs text-amber-800 bg-amber-50 rounded-full px-2 py-0.5"
                          >
                            <AlertTriangle size={12} /> Not clearly grounded
                          </span>
                        )}

                        {/* show each source as a small chip with the file name and page */}
                        {turn.citations.map((c) => (
                          <span
                            key={c.number}
                            id={`turn-${i}-source-${c.number}`}
                            title={`${c.source} (chunk ${c.chunk_index})`}
                            className="inline-flex items-center gap-1 text-xs text-slate-600 bg-white border border-slate-200 rounded-lg px-2 py-0.5 scroll-mt-4 target:border-teal-400 target:bg-teal-50 target:text-teal-800"
                          >
                            <FileText size={12} />
                            <span className="font-medium text-teal-700">{c.number}</span>
                            {c.source.split("/").pop()}
                            <span className="text-slate-400">p.{c.page}</span>
                          </span>
                        ))}
                      </div>

                      {/* explain the reason when the answer is not grounded */}
                      {turn.grounded === false && turn.grounding_reason && (
                        <div className="text-xs text-amber-700 mt-1.5">
                          {turn.grounding_reason}, so this answer may be unreliable
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* show the input with a round send button */}
      <form
        className="w-full max-w-3xl mx-auto flex items-center gap-2 bg-white border border-slate-300 rounded-xl pl-4 pr-1.5 py-1.5 focus-within:border-teal-500 focus-within:ring-2 focus-within:ring-teal-100"
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your documents"
          className="flex-1 bg-transparent text-sm focus:outline-none placeholder:text-slate-400"
        />
        <button
          type="submit"
          aria-label="send question"
          disabled={!input.trim() || sending}
          className="w-8 h-8 rounded-lg bg-teal-700 text-white flex items-center justify-center hover:bg-teal-800 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <ArrowUp size={16} />
        </button>
      </form>
    </div>
  );
}
