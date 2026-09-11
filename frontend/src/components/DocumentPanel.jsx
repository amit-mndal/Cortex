import { useRef, useState } from "react";
import { API_BASE } from "../config.js";

export default function DocumentPanel({ documents, setDocuments }) {
  const fileInput = useRef(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
      const data = await res.json();
      setDocuments((prev) => [...prev, data]);
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }


  async function handleDelete(docId) {
    try {
      await fetch(`${API_BASE}/documents/${docId}`, { method: "DELETE" });
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
    } catch (err) {
      console.error("Delete failed", err);
    }
  }

  return (
    <aside className="w-72 shrink-0 border-r border-graphite-700 bg-graphite-900 flex flex-col">
      <div className="px-5 py-6 border-b border-graphite-700">
        {/* <h1 className="font-serif text-2xl text-paper-100 tracking-tight">Cortex</h1> */}
        <h1 className="font-sans text-2xl text-paper-100 tracking-tight">Cortex</h1>
        <p className="text-xs text-paper-600 mt-1 tracking-wide uppercase">Research Agent</p>
      </div>

      <div className="p-5">
        <button
          onClick={() => fileInput.current.click()}
          disabled={uploading}
          className="w-full border border-moss-500 text-moss-400 rounded-sm py-2.5 text-sm font-medium
                     hover:bg-moss-500 hover:text-graphite-950 transition-colors duration-150 disabled:opacity-50"
        >
          {uploading ? "Ingesting…" : "+ Add document"}
        </button>
        <input ref={fileInput} type="file" accept=".pdf,.txt,.csv" onChange={handleFile} className="hidden" />
      </div>

      <div className="flex-1 overflow-y-auto px-5 pb-5">
        <p className="text-[11px] uppercase tracking-widest text-paper-600 mb-3">
          Library — {documents.length}
        </p>
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li
              key={doc.doc_id}
              className="group relative border border-graphite-700 rounded-sm px-3 py-2.5 bg-graphite-800"
            >
              <p className="text-sm text-paper-200 truncate pr-5">{doc.filename}</p>
              <p className="text-[11px] text-paper-600 mt-0.5 font-mono">
                {doc.filename.toLowerCase().endsWith(".csv")
                  ? "ready for analysis"
                  : `${doc.num_chunks} chunks indexed`}
              </p>
              <button
                onClick={() => handleDelete(doc.doc_id)}
                className="absolute top-2 right-2 opacity-0 group-hover:opacity-100
                          transition-opacity text-paper-600 hover:text-red-400 text-xs"
                title="Delete document"
              >
                ✕
              </button>
            </li>
            // <li
            //   key={doc.doc_id}
            //   className="border border-graphite-700 rounded-sm px-3 py-2.5 bg-graphite-800"
            // >
            //   <p className="text-sm text-paper-200 truncate">{doc.filename}</p>
            //   <p className="text-[11px] text-paper-600 mt-0.5 font-mono">
            //     {doc.filename.toLowerCase().endsWith(".csv")
            //       ? "ready for analysis"
            //       : `${doc.num_chunks} chunks indexed`}
            //   </p>
            // </li>
          ))}
          {documents.length === 0 && (
            <li className="text-sm text-paper-600 italic">No documents yet.</li>
          )}
        </ul>
      </div>
    </aside>
  );
}
