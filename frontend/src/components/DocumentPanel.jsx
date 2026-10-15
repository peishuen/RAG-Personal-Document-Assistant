/*
This file is the documents panel on the top left of the screen.
The user can open the upload box, tick documents to limit the search, and delete documents.
*/
import { useState } from "react";
import { FileText, Files, FolderOpen, Trash2, Upload } from "lucide-react";
import { deleteDocument } from "../api.js";
import UploadModal from "./UploadModal.jsx";

// pick an icon color by file type, so pdf and text files look different
const fileIconColor = (type) => (type === "text" ? "text-slate-500" : "text-amber-600");

// show only the file name, and hide the folder path
const shortName = (source) => source.split("/").pop();

export default function DocumentPanel({ documents, selectedSources, setSelectedSources, onChanged }) {
  // track if the upload pop-up box is open
  const [uploadOpen, setUploadOpen] = useState(false);

  // add the document to the search list if it is not there, or remove it if it is
  const toggleSource = (source) => {
    setSelectedSources((prev) =>
      prev.includes(source) ? prev.filter((s) => s !== source) : [...prev, source]
    );
  };

  // delete the document, then refresh the list
  const removeDocument = async (source) => {
    await deleteDocument(source);
    onChanged();
  };

  return (
    <div className="flex flex-col h-full gap-2">
      <div className="flex items-center gap-2 shrink-0">
        {/* show an icon chip, the title, and how many documents there are */}
        <span className="w-7 h-7 rounded-lg bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center">
          <Files size={15} />
        </span>
        <span className="font-medium text-sm text-slate-800">Documents</span>
        <span className="bg-slate-100 text-slate-600 rounded-full px-2 text-[11px]">{documents.length}</span>
        {/* open the upload pop-up box */}
        <button
          onClick={() => setUploadOpen(true)}
          className="ml-auto inline-flex items-center gap-1 rounded-md border border-teal-200 px-2 py-1 text-xs text-teal-700 hover:bg-teal-50"
        >
          <Upload size={14} /> Upload
        </button>
      </div>

      {/* show the upload pop-up box, and refresh the list when files are added */}
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} onUploaded={onChanged} />

      {/* show the document list, or a message if there are none */}
      {documents.length > 0 ? (
        <>
          <div className="shrink-0 text-[11px] text-slate-400">
            tick documents to limit the search, or leave all unticked to search everything
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto divide-y divide-slate-100">
            {documents.map((doc) => (
              <div key={doc.source} className="group flex items-center gap-2 py-2 text-xs">
                <input
                  type="checkbox"
                  checked={selectedSources.includes(doc.source)}
                  onChange={() => toggleSource(doc.source)}
                  className="accent-teal-700"
                />
                <FileText size={20} strokeWidth={1.5} className={`shrink-0 ${fileIconColor(doc.type)}`} />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-slate-800 truncate" title={doc.source}>{shortName(doc.source)}</div>
                  <div className="text-slate-400 text-[11px]">{doc.page_count} page(s), {doc.chunk_count} chunk(s)</div>
                </div>
                <button
                  onClick={() => removeDocument(doc.source)}
                  title="delete this document"
                  aria-label="delete this document"
                  className="p-1 rounded text-slate-300 hover:text-red-600 hover:bg-red-50 group-hover:text-slate-400"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center gap-1 text-center text-slate-400">
          <FolderOpen size={24} strokeWidth={1.5} />
          <div className="text-xs font-medium text-slate-500">No documents yet</div>
          <div className="text-[11px]">upload a pdf or text file to get started</div>
        </div>
      )}
    </div>
  );
}
