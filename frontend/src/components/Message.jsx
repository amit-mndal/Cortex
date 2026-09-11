import ReactMarkdown from "react-markdown";

const ROUTE_LABELS = {
  rag: "Document agent",
  web: "Web-search agent",
  data: "Data-analysis agent",
  chat: "General chat",
};

export default function Message({ role, content, sources = [], retries = 0, route, fromCache, eval: evalScores }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-2xl ${isUser ? "" : "w-full"}`}>
        {!isUser && route && (
          <p className="text-[11px] font-mono text-moss-400 mb-1.5 tracking-wide uppercase">
            {ROUTE_LABELS[route] || route}
            {retries > 0 && <span className="text-gold-500"> · refined search × {retries}</span>}
            {fromCache && <span className="text-gold-500"> · cached</span>}
          </p>
        )}

        <div
          className={
            isUser
              ? "bg-moss-600 text-paper-100 rounded-xl px-4 py-3 text-[15px] leading-relaxed"
              : "bg-graphite-800 border border-graphite-700 rounded-xl px-5 py-4 text-[15px] leading-relaxed text-paper-200"
          }
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && sources.length > 0 && (
          <div className="mt-2.5 border-l-2 border-gold-500/40 pl-3">
            <p className="text-[11px] uppercase tracking-widest text-paper-600 mb-1.5">Sources</p>
            <ul className="space-y-1">
              {sources.map((s) => (
                <li key={s.index} className="text-[13px] text-paper-400 font-mono">
                  {/* <span className="text-gold-500">[{s.index}]</span> {s.filename} —{" "} */}
                  <span className="text-gold-500">[{s.index}]</span> {s.filename}
                    {s.page ? `, p.${s.page}` : ""} —{" "}
                  <span className="italic text-paper-600">"{s.text.slice(0, 90)}…"</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {!isUser && evalScores && (
          <div className="mt-2 flex gap-4 text-[11px] font-mono text-paper-600">
            <span>
              faithfulness <span className="text-moss-400">{(evalScores.faithfulness_score * 100).toFixed(0)}%</span>
            </span>
            <span>
              relevance <span className="text-moss-400">{(evalScores.relevance_score * 100).toFixed(0)}%</span>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
