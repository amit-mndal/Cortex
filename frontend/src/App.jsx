import { useState, useRef, useEffect } from "react";
import DocumentPanel from "./components/DocumentPanel.jsx";
import Message from "./components/Message.jsx";
import { API_BASE } from "./config.js";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [progressSteps, setProgressSteps] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading, progressSteps]);

  async function sendQuestion() {
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    setProgressSteps([]);

    try {
      const res = await fetch(`${API_BASE}/ask-async`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const { job_id } = await res.json();

      const source = new EventSource(`${API_BASE}/stream/${job_id}`);

      source.addEventListener("progress", (e) => {
        const data = JSON.parse(e.data);
        setProgressSteps((prev) => [...prev, data.message]);
      });

      source.addEventListener("result", (e) => {
        const data = JSON.parse(e.data);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.answer || data.error || "No answer produced.",
            sources: data.sources,
            retries: data.retries,
            route: data.route,
            fromCache: data.from_cache,
            eval: data.eval,
          },
        ]);
        setLoading(false);
        setProgressSteps([]);
        source.close();
      });

      source.onerror = () => {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Lost connection to the agent stream. Is the backend/worker running?" },
        ]);
        setLoading(false);
        setProgressSteps([]);
        source.close();
      };
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong reaching the agent. Is the backend running?" },
      ]);
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion();
    }
  }

  return (
    <div className="h-screen flex bg-graphite-950">
      <DocumentPanel documents={documents} setDocuments={setDocuments} />

      <main className="flex-1 flex flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-8">
          <div className="max-w-2xl mx-auto space-y-5">
            {messages.length === 0 && (
              <div className="text-center pt-24">
                {/* <p className="font-serif text-3xl text-paper-200">Ask something.</p> */}
                <p className="font-sans text-3xl text-paper-200">Ask anything..</p>
                <p className="text-paper-600 text-sm mt-2">
                  Upload a PDF for document Q&amp;A or a CSV for data analysis or just ask
                  anything. A supervisor agent routes each question to the right specialist:
                  document search, live web search or code-based data analysis.
                </p>
              </div>
            )}
            {messages.map((m, i) => (
              <Message key={i} {...m} />
            ))}
            {loading && (
              <div className="space-y-1">
                {progressSteps.map((step, i) => (
                  <p key={i} className="text-paper-600 text-[13px] font-mono">
                    <span className="text-moss-400">›</span> {step}
                  </p>
                ))}
                {progressSteps.length === 0 && (
                  <p className="text-paper-600 text-[13px] font-mono animate-pulse">Starting agent…</p>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-graphite-700 px-8 py-5">
          <div className="max-w-2xl mx-auto flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder="Ask about your documents or anything you like…"
              className="flex-1 bg-graphite-800 border border-graphite-700 rounded-xl px-4 py-3
                         text-paper-100 text-[15px] placeholder-paper-600 focus:outline-none
                         focus:border-moss-500 resize-none"
            />
            <button
              onClick={sendQuestion}
              disabled={loading}
              className="bg-moss-500 text-graphite-950 font-medium rounded-xl px-5
                         hover:bg-moss-400 transition-colors disabled:opacity-50"
            >
              Ask
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
