// *** chat panel: shows past turns, centered suggested prompts, and sends new questions to the backend ***
import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Bot, CheckCircle2, Loader2, MessageCircle, User } from "lucide-react";
import { askQuestion, getSession } from "../api.js";
import { clearPending, markPending } from "../pendingRequests.js";

// grounding finishes a moment after the answer, poll a few times until it shows up
const GROUNDING_POLL_MS = 1000;
const GROUNDING_MAX_ATTEMPTS = 10;

const SUGGESTED_PROMPTS = [
  "Summarize the key points across all my documents",
  "What are the main findings?",
  "Compare the documents I've uploaded",
  "Explain this in simple terms",
];

// turns a literal "[Source 2]" or "[2]" in the answer text into a link to that source's entry below
function renderAnswer(answer, turnIndex) {
  const pieces = answer.split(/(\[Source \d+\]|\[\d+\])/g);

  return pieces.map((piece, i) => {
    const match = piece.match(/^\[(?:Source )?(\d+)\]$/);
    if (!match) return piece;

    const number = match[1];
    return (
      <a
        key={i}
        href={`#turn-${turnIndex}-source-${number}`}
        className="inline-flex items-center justify-center w-5 h-5 mx-0.5 rounded-full bg-teal-100 text-teal-700 text-[11px] font-semibold align-middle hover:bg-teal-200"
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

  // jump to the newest message whenever the turn list changes, new question, answer
  // arriving, or grounding resolving all count, so the latest content is always in view
  useEffect(() => {
    const box = scrollBoxRef.current;
    if (box) box.scrollTop = box.scrollHeight;
  }, [turns]);

  // ask() and pollForGrounding() are async and can resolve long after the user has switched
  // sessions, this ref always holds whichever session is on screen right now so a stale
  // response can tell it no longer applies, instead of overwriting the wrong session's turns
  const activeSessionIdRef = useRef(sessionId);
  useEffect(() => {
    activeSessionIdRef.current = sessionId;
    // a different session's in-flight request should never block typing in this one
    setSending(false);
  }, [sessionId]);

  // keeps re-fetching the session until this turn's grounding check lands, then applies it
  const pollForGrounding = (forSessionId, turnIndex, attempt = 0) => {
    if (attempt >= GROUNDING_MAX_ATTEMPTS) return;

    setTimeout(async () => {
      const data = await getSession(forSessionId);
      const updatedTurn = data.turns[turnIndex];

      if (updatedTurn && updatedTurn.grounded !== null) {
        if (forSessionId === activeSessionIdRef.current) {
          setTurns((prev) => {
            const updated = [...prev];
            updated[turnIndex] = updatedTurn;
            return updated;
          });
        }
      } else {
        pollForGrounding(forSessionId, turnIndex, attempt + 1);
      }
    }, GROUNDING_POLL_MS);
  };

  const ask = async (question) => {
    if (!question || !sessionId || sending) return;
    const forSessionId = sessionId;
    setInput("");
    setSending(true);
    markPending(forSessionId, question);

    // render the user's question immediately; the assistant row below fills in once the pipeline returns
    let turnIndex;
    setTurns((prev) => {
      turnIndex = prev.length;
      return [...prev, { question, pending: true }];
    });

    const turn = await askQuestion(forSessionId, question, selectedSources);
    clearPending(forSessionId);
    setSending(false);
    onAnswered();

    // the backend already persisted this turn to forSessionId's file regardless, only touch
    // the on-screen turns if the user is still actually looking at that same session
    if (forSessionId === activeSessionIdRef.current) {
      setTurns((prev) => {
        const updated = [...prev];
        updated[turnIndex] = turn;
        return updated;
      });

      // the answer is already shown, grounding is still running in the background on the server
      if (turn.grounded === null) {
        pollForGrounding(forSessionId, turnIndex);
      }
    }
  };

  if (!hasDocuments) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center gap-2 text-slate-400">
        <MessageCircle size={28} />
        <div className="font-semibold text-base text-slate-600">Ask your documents</div>
        <div className="text-sm">upload and store at least one document before asking a question</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-2">
      <div ref={scrollBoxRef} className="flex-1 min-h-0 overflow-y-auto border border-slate-200 rounded-lg bg-white p-4 flex flex-col">
        {turns.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-700">What would you like to know?</h3>
              <p className="text-slate-400 text-sm">pick a suggestion or type your own question below</p>
            </div>
            <div className="grid grid-cols-2 gap-2 max-w-xl w-full">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => ask(prompt)}
                  className="border border-slate-200 rounded-xl p-3 text-sm text-slate-600 hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700 transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          turns.map((turn, i) => (
            <div key={i} className="flex flex-col gap-3 mb-5">
              <div className="flex items-start gap-3">
                <div className="shrink-0 w-7 h-7 rounded-full bg-teal-600 text-white flex items-center justify-center">
                  <User size={14} />
                </div>
                <div className="pt-0.5 font-medium text-slate-800">{turn.question}</div>
              </div>

              <div className="flex items-start gap-3">
                <div className="shrink-0 w-7 h-7 rounded-full bg-slate-700 text-white flex items-center justify-center">
                  <Bot size={14} />
                </div>

                {turn.pending ? (
                  <div className="flex-1 pt-2.5">
                    <div className="h-1.5 w-32 bg-teal-100 rounded-full loading-bar-track text-teal-500">
                      <div className="loading-bar-fill" />
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 pt-0.5 text-slate-700">
                    <div className="whitespace-pre-wrap">{renderAnswer(turn.answer, i)}</div>

                    {turn.grounded === null ? (
                      <div className="inline-flex items-center gap-1 mt-2 text-xs text-slate-400">
                        <Loader2 size={12} className="animate-spin" /> checking groundedness...
                      </div>
                    ) : turn.grounded ? (
                      <div className="inline-flex items-center gap-1 mt-2 text-xs text-green-700 bg-green-50 rounded-full px-2 py-0.5">
                        <CheckCircle2 size={12} /> grounded: {turn.grounding_reason}
                      </div>
                    ) : (
                      <div className="inline-flex items-center gap-1 mt-2 text-xs text-amber-700 bg-amber-50 rounded-full px-2 py-0.5">
                        <AlertTriangle size={12} /> not clearly grounded: {turn.grounding_reason}, answer may be unreliable
                      </div>
                    )}

                    <div className="text-xs font-semibold text-slate-500 mt-2">Sources</div>
                    <div className="flex flex-col gap-0.5 mt-1">
                      {turn.citations.map((c) => (
                        <div
                          key={c.number}
                          id={`turn-${i}-source-${c.number}`}
                          className="text-xs text-slate-500 rounded px-1 -mx-1 target:bg-teal-50 target:text-teal-700 scroll-mt-4"
                        >
                          <span className="font-semibold text-teal-600">[{c.number}]</span> {c.source} (page{" "}
                          {c.page}, chunk {c.chunk_index})
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="ask a question about your uploaded documents"
          className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-200 focus:border-teal-400"
        />
      </form>
    </div>
  );
}
