/*
This file is the upload pop-up box.
The user can drag files into it or browse for them, then press upload.
The loading bar shows inside the box, and the box closes by itself when the upload is done.
*/
import { useEffect, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, CloudUpload, FileText, X } from "lucide-react";
import { uploadDocuments } from "../api.js";

// set the limits, so a big upload cannot overload the small free server
const MAX_FILES = 5;
const MAX_FILE_MB = 10;
const ALLOWED_EXTENSIONS = [".pdf", ".txt"];

// how long to show the success message before closing the box
const CLOSE_DELAY_MS = 1200;

// turn a size in bytes into a short label like "2.8 MB"
const formatSize = (bytes) =>
  bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;

export default function UploadModal({ open, onClose, onUploaded }) {
  const [files, setFiles] = useState([]);
  const [dragging, setDragging] = useState(false);
  // track the stage: "idle", "uploading", "done" or "error"
  const [phase, setPhase] = useState("idle");
  const [message, setMessage] = useState("");
  const inputRef = useRef(null);

  const uploading = phase === "uploading";

  // reset everything each time the box opens
  useEffect(() => {
    if (open) {
      setFiles([]);
      setDragging(false);
      setPhase("idle");
      setMessage("");
    }
  }, [open]);

  // close the box with the Escape key, except while uploading
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e) => {
      if (e.key === "Escape" && !uploading) onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, uploading, onClose]);

  if (!open) return null;

  // add new files to the list, and skip the ones that are not allowed
  const addFiles = (incoming) => {
    const problems = [];
    const next = [...files];

    for (const file of incoming) {
      const lowerName = file.name.toLowerCase();

      if (!ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext))) {
        problems.push(`${file.name} is not a PDF or text file`);
      } else if (file.size > MAX_FILE_MB * 1024 * 1024) {
        problems.push(`${file.name} is bigger than ${MAX_FILE_MB} MB`);
      } else if (next.some((f) => f.name === file.name && f.size === file.size)) {
        // ignore a file that is already in the list
        continue;
      } else if (next.length >= MAX_FILES) {
        problems.push(`only ${MAX_FILES} files at a time`);
        break;
      } else {
        next.push(file);
      }
    }

    setFiles(next);
    setPhase(problems.length ? "error" : "idle");
    setMessage(problems.join(". "));
  };

  // remove one file from the list
  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setPhase("idle");
    setMessage("");
  };

  // read the files dropped into the box
  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (uploading) return;
    addFiles(Array.from(e.dataTransfer.files));
  };

  // read the files picked from the file explorer
  const handleBrowse = (e) => {
    addFiles(Array.from(e.target.files));
    // clear the input so the same file can be picked again
    e.target.value = "";
  };

  // send the files, show the result, then close the box
  const handleUpload = async () => {
    if (!files.length || uploading) return;
    setPhase("uploading");
    setMessage("");

    try {
      const result = await uploadDocuments(files);

      // treat a reply without the expected lists as a failed upload
      if (!Array.isArray(result.stored)) throw new Error("unexpected response");
      const stored = result.stored.length;
      const skipped = result.skipped?.length ?? 0;

      setPhase("done");
      setMessage(
        skipped ? `Added ${stored} file(s), skipped ${skipped} duplicate(s).` : `Added ${stored} file(s).`
      );

      // refresh the list behind the box, then close after a short pause
      onUploaded();
      setTimeout(onClose, CLOSE_DELAY_MS);
    } catch {
      setPhase("error");
      setMessage("Upload failed. Please try again.");
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onMouseDown={(e) => {
        // close when the dark background is clicked, except while uploading
        if (e.target === e.currentTarget && !uploading) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-title"
        className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-xl p-5 flex flex-col gap-4"
      >
        <div className="flex items-center justify-between">
          <h2 id="upload-title" className="text-base font-medium text-slate-800">Upload documents</h2>
          <button
            onClick={onClose}
            disabled={uploading}
            aria-label="close"
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:pointer-events-none"
          >
            <X size={18} />
          </button>
        </div>

        {/* show the drop area, with a highlight when a file is dragged over it */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            if (!uploading) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`flex flex-col items-center gap-2 rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors ${
            dragging ? "border-teal-500 bg-teal-50" : "border-slate-300 bg-slate-50"
          } ${uploading ? "opacity-50" : ""}`}
        >
          <CloudUpload size={32} strokeWidth={1.5} className="text-teal-700" />
          <div className="text-sm text-slate-700">Drag and drop files here</div>
          <div className="text-xs text-slate-400">or</div>
          <button
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="rounded-md border border-teal-200 bg-white px-3 py-1.5 text-xs text-teal-700 hover:bg-teal-50 disabled:pointer-events-none"
          >
            Browse files
          </button>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.txt"
            onChange={handleBrowse}
            className="hidden"
          />
          <div className="text-[11px] text-slate-400">
            PDF or text, up to {MAX_FILES} files, {MAX_FILE_MB} MB each
          </div>
        </div>

        {/* list the chosen files, with a button to remove each one */}
        {files.length > 0 && (
          <div className="flex flex-col divide-y divide-slate-100 max-h-40 overflow-y-auto border border-slate-200 rounded-lg">
            {files.map((file, i) => (
              <div key={`${file.name}-${file.size}`} className="flex items-center gap-2 px-3 py-2 text-xs">
                <FileText size={16} strokeWidth={1.5} className="shrink-0 text-slate-500" />
                <span className="flex-1 min-w-0 truncate text-slate-700" title={file.name}>{file.name}</span>
                <span className="text-slate-400">{formatSize(file.size)}</span>
                {!uploading && phase !== "done" && (
                  <button
                    onClick={() => removeFile(i)}
                    aria-label={`remove ${file.name}`}
                    className="p-0.5 rounded text-slate-300 hover:text-red-600 hover:bg-red-50"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* show the moving loading bar while the files are uploaded and processed */}
        {uploading && (
          <div role="status" aria-live="polite">
            <div className="h-1.5 w-full bg-teal-100 rounded-full loading-bar-track text-teal-600">
              <div className="loading-bar-fill" />
            </div>
            <div className="text-xs text-slate-500 mt-1.5">
              Uploading and processing {files.length} file(s)... scanned files can take a minute
            </div>
          </div>
        )}

        {/* show the result, or the reason a file was not accepted */}
        {!uploading && message && (
          <div
            role={phase === "error" ? "alert" : "status"}
            className={`flex items-start gap-1.5 text-xs ${phase === "error" ? "text-red-600" : "text-emerald-700"}`}
          >
            {phase === "error" ? <AlertCircle size={14} className="mt-0.5 shrink-0" /> : <CheckCircle2 size={14} className="mt-0.5 shrink-0" />}
            <span>{message}</span>
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={uploading}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none"
          >
            {phase === "done" ? "Close" : "Cancel"}
          </button>
          <button
            onClick={handleUpload}
            disabled={!files.length || uploading || phase === "done"}
            className="rounded-lg bg-teal-700 px-3 py-1.5 text-sm text-white hover:bg-teal-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {files.length ? `Upload ${files.length} file(s)` : "Upload"}
          </button>
        </div>
      </div>
    </div>
  );
}
