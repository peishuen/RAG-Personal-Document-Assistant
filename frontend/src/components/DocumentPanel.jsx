// *** document panel: upload files, scope checkboxes, delete stored documents ***
import { FileText, Trash2 } from "lucide-react";
import { deleteDocument, uploadDocuments } from "../api.js";

export default function DocumentPanel({ documents, selectedSources, setSelectedSources, onChanged }) {
  const handleUpload = async (e) => {
    const files = e.target.files;
    if (!files.length) return;
    await uploadDocuments(files);
    e.target.value = "";
    onChanged();
  };

  const toggleSource = (source) => {
    setSelectedSources((prev) =>
      prev.includes(source) ? prev.filter((s) => s !== source) : [...prev, source]
    );
  };

  const removeDocument = async (source) => {
    await deleteDocument(source);
    onChanged();
  };

  return (
    <div className="flex flex-col h-full gap-2">
      <div className="flex items-center gap-2 text-teal-700 shrink-0">
        <FileText size={18} />
        <span className="font-semibold text-base">Documents</span>
      </div>
      <input
        type="file"
        multiple
        accept=".pdf,.txt"
        onChange={handleUpload}
        className="shrink-0 text-xs text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-teal-50 file:px-3 file:py-1.5 file:text-teal-700 file:font-medium hover:file:bg-teal-100"
      />
      {documents.length > 0 ? (
        <>
          <div className="shrink-0 text-xs text-slate-500">
            check document(s) to limit search to them, leave all unchecked to search everything
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto border border-teal-100 rounded-lg bg-teal-50/60 divide-y divide-teal-100">
            {documents.map((doc) => (
              <div
                key={doc.source}
                className="flex items-center gap-2 px-3 py-2 text-xs hover:bg-white transition-colors"
              >
                <input
                  type="checkbox"
                  checked={selectedSources.includes(doc.source)}
                  onChange={() => toggleSource(doc.source)}
                  className="accent-teal-600"
                />
                <div className="flex-1">
                  <div className="font-semibold text-slate-700">{doc.source}</div>
                  <div className="text-slate-400">{doc.page_count} page(s), {doc.chunk_count} chunk(s)</div>
                </div>
                <button
                  onClick={() => removeDocument(doc.source)}
                  title="delete this document"
                  className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="text-xs text-slate-400">no documents uploaded yet</div>
      )}
    </div>
  );
}
