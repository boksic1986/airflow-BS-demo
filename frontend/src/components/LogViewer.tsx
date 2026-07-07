import {Copy, Search} from "lucide-react";
import {useMemo, useState} from "react";

import type {LogStream, RunLog} from "../api";

const streams: LogStream[] = ["metadata", "stdout", "stderr"];

export function LogViewer({
  stream,
  onStreamChange,
  log,
  error,
}: {
  stream: LogStream;
  onStreamChange: (stream: LogStream) => void;
  log: RunLog | null;
  error: string | null;
}) {
  const [query, setQuery] = useState("");
  const lines = log?.lines || [];
  const matching = useMemo(() => {
    if (!query.trim()) return lines;
    const needle = query.toLowerCase();
    return lines.filter((line) => line.toLowerCase().includes(needle));
  }, [lines, query]);

  async function copyVisible() {
    await navigator.clipboard?.writeText(matching.join("\n"));
  }

  return (
    <section className="panel">
      <div className="section-heading split">
        <h2>Logs</h2>
        <button className="button ghost" type="button" onClick={() => void copyVisible()} aria-label="Copy visible log excerpt">
          <Copy size={15} />
          Copy
        </button>
      </div>
      <div className="tabs compact-tabs" role="tablist" aria-label="Log stream">
        {streams.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={stream === item}
            className={stream === item ? "active" : ""}
            onClick={() => onStreamChange(item)}
          >
            {item}
          </button>
        ))}
      </div>
      <label className="search-field">
        <Search size={15} />
        <span className="sr-only">Search logs</span>
        <input aria-label="Search logs" value={query} placeholder="Search logs" onChange={(event) => setQuery(event.target.value)} />
      </label>
      {query ? <p className="muted">{matching.length} matching line{matching.length === 1 ? "" : "s"}</p> : null}
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      <div className="log-viewer" aria-label={`${stream} log`}>
        {matching.length ? (
          matching.map((line, index) => (
            <div className={/error|exception|failed|traceback/i.test(line) ? "log-line error-line" : "log-line"} key={`${line}-${index}`}>
              {line}
            </div>
          ))
        ) : (
          <span className="empty-state">No log lines returned.</span>
        )}
      </div>
      {log ? <p className="muted path-text">Path: {log.path}</p> : null}
    </section>
  );
}
