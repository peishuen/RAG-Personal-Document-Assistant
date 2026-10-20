/*
This file is the source pop-up box.
When the user clicks a source chip under an answer, it shows the original text of
that chunk, together with its info (file, page, chunk number, type and length).
*/
import { useEffect, useState } from "react";
import { AlertCircle, Check, Copy, FileText, Loader2, X } from "lucide-react";
import { getChunk } from "../api.js";

// turn the stored type into a label that is easier to read
const TYPE_LABELS = {
  pdf: "PDF",
  scanned: "Scanned PDF (read with OCR)",
  text: "Text file",
};

// show only the file name, and hide the folder path
const shortName = (source) => source.split("/").pop();

export default function SourceModal({ citation, onClose }) {
  const [chunk, setChunk] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  // load the chunk each time a different citation is opened
  useEffect(() => {
    if (!citation) return;

    // use a flag, so an old answer does not replace a newer one
    let cancelled = false;
    setChunk(null);
    setError("");
    setCopied(false);

    getChunk(citation.source, citation.page, citation.chunk_index)
      .then((data) => {
        if (!cancelled) setChunk(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, [citation]);

  // close the box with the Escape key
  useEffect(() => {
    if (!citation) return;
    const onKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [citation, onClose]);

  if (!citation) return null;

  // copy the chunk text, and show a tick for two seconds
  const copyText = async () => {
    try {
      await navigator.clipboard.writeText(chunk.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore the error, because some browsers block clipboard access
    }
  };

  // list the info to show, using the saved metadata
  const details = chunk
    ? [
        ["File", shortName(chunk.metadata.source)],
        ["Page", chunk.metadata.page],
        ["Chunk", chunk.metadata.chunk_index],
        ["Type", TYPE_LABELS[chunk.metadata.type] || chunk.metadata.type],
        ["Length", `${chunk.characters.toLocaleString()} characters`],
      ]
    : [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onMouseDown={(e) => {
        // close when the dark background is clicked
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-title"
        className="w-full max-w-xl max-h-[85vh] bg-white rounded-2xl border border-slate-200 shadow-xl p-5 flex flex-col gap-4"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className="shrink-0 w-7 h-7 rounded-lg bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center">
              <FileText size={15} />
            </span>
            <div className="min-w-0">
              <h2 id="source-title" className="text-base font-medium text-slate-800">Source {citation.number}</h2>
              <div className="text-xs text-slate-500 truncate" title={citation.source}>{shortName(citation.source)}</div>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="close"
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100"
          >
            <X size={18} />
          </button>
        </div>

        {/* show a loading line while the chunk is fetched */}
        {!chunk && !error && (
          <div role="status" className="flex items-center gap-2 text-sm text-slate-500 py-6 justify-center">
            <Loader2 size={16} className="animate-spin" /> Loading source...
          </div>
        )}

        {/* show the reason when the chunk could not be loaded */}
        {error && (
          <div role="alert" className="flex items-start gap-1.5 text-sm text-red-600 py-4">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {chunk && (
          <>
            {/* show the info about this chunk as small labeled boxes */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {details.map(([label, value]) => (
                <div key={label} className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2 min-w-0">
                  <div className="text-[11px] text-slate-400">{label}</div>
                  <div className="text-xs text-slate-700 truncate" title={String(value)}>{value}</div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-600">Original text</span>
              <button
                onClick={copyText}
                className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
              >
                {copied ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                {copied ? "Copied" : "Copy text"}
              </button>
            </div>

            {/* show the chunk text exactly as it was stored, with its line breaks */}
            <div className="min-h-0 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-700 whitespace-pre-wrap">
              {chunk.text}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
