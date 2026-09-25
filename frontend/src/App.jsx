import { useState } from "react";
import "./App.css";

function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const askQuestion = async (event) => {
    event.preventDefault();
    const text = question.trim();
    if (!text || loading) return;

    setMessages((previous) => [...previous, { role: "user", text }]);
    setQuestion("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text }),
      });

      if (!response.ok) {
        throw new Error(`Backend returned HTTP ${response.status}`);
      }

      const data = await response.json();
      setMessages((previous) => [
        ...previous,
        {
          role: "bot",
          sql: data.sql,
          result: data.result,
          error: data.error,
          finalAnswer: data.final_answer,
        },
      ]);
    } catch {
      setMessages((previous) => [
        ...previous,
        {
          role: "bot",
          error: "Failed to reach the backend. Make sure FastAPI is running on port 8000.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="#top" aria-label="Taxi Query home">
          <span className="wordmark-mark" aria-hidden="true">T</span>
          <span>FIELDNOTES <b>/ DATA</b></span>
        </a>
        <span className="dataset-label"><span className="status-dot" /> NYC TAXI DATA</span>
      </header>

      <section className="workspace" id="top">
        <div className="page-heading">
          <p className="eyebrow">NATURAL LANGUAGE QUERY</p>
          <h1>Ask the data.</h1>
          <p className="heading-note">Explore taxi trips with plain English. Every answer comes with the SQL behind it.</p>
        </div>

        <section className="conversation" aria-label="Analytics conversation">
          <div className="conversation-bar">
            <span>QUERY SESSION</span>
            <span className="session-indicator">{loading ? "RUNNING QUERY" : "READY"}</span>
          </div>

          <div className="chat-window" aria-live="polite" aria-busy={loading}>
            {messages.length === 0 ? (
              <div className="empty-state">
                <span className="empty-index">01 / START HERE</span>
                <p>How far does the average taxi ride go?</p>
                <button
                  className="suggestion"
                  type="button"
                  onClick={() => setQuestion("What is the average trip distance?")}
                >
                  Use example question <span aria-hidden="true">↗</span>
                </button>
              </div>
            ) : (
              messages.map((message, index) => (
                <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                  <div className="message-label">{message.role === "user" ? "YOU" : "ANALYTICS AGENT"}</div>
                  {message.role === "user" ? (
                    <p className="user-question">{message.text}</p>
                  ) : message.error ? (
                    <p className="error-message" role="alert">{message.error}</p>
                  ) : (
                    <div className="answer-content">
                      {message.sql && (
                        <section className="output-section">
                          <h2><span>01</span> GENERATED SQL</h2>
                          <pre className="sql-block"><code>{message.sql}</code></pre>
                        </section>
                      )}
                      {message.result != null && (
                        <section className="output-section">
                          <h2><span>02</span> QUERY RESULT</h2>
                          <pre className="result-block">{typeof message.result === "string" ? message.result : JSON.stringify(message.result, null, 2)}</pre>
                        </section>
                      )}
                      {!message.sql && message.result == null && message.finalAnswer && (
                        <p className="final-answer">{message.finalAnswer}</p>
                      )}
                    </div>
                  )}
                </article>
              ))
            )}
            {loading && <p className="loading"><span /> Generating query and checking results</p>}
          </div>

          <form className="input-row" onSubmit={askQuestion}>
            <label className="sr-only" htmlFor="question-input">Ask a question about the taxi data</label>
            <input
              id="question-input"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a question about the taxi data..."
              disabled={loading}
            />
            <button type="submit" disabled={loading || !question.trim()}>
              Ask <span aria-hidden="true">↗</span>
            </button>
          </form>
          <p className="input-hint">Press Enter to run your query</p>
        </section>
      </section>

      <footer className="footer"><span>TEXT-TO-SQL ANALYTICS AGENT</span><span>DUCKDB <i>·</i> FASTAPI <i>·</i> REACT</span></footer>
    </main>
  );
}

export default App;
