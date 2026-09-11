import {Copy, Search} from "lucide-react";
import {useEffect, useMemo, useState} from "react";

import type {LogStream, RunLog, RunLogIndexItem} from "../api";

const streams: LogStream[] = ["metadata", "stdout", "stderr"];

export function LogViewer({
  stream,
  onStreamChange,
  log,
  error,
  sources = [],
  activeKey,
  onKeyChange,
  onSearch,
}: {
  stream: LogStream;
  onStreamChange: (stream: LogStream) => void;
  log: RunLog | null;
  error: string | null;
  sources?: RunLogIndexItem[];
  activeKey?: string | null;
  onKeyChange?: (key: string) => void;
  onSearch?: (query: string) => void;
}) {
  const [query, setQuery] = useState("");
  useEffect(() => {
    if (!onSearch) return;
    const timer = setTimeout(() => onSearch(query.trim()), 350);
    return () => clearTimeout(timer);
  }, [query, onSearch]);
  const searching = Boolean(onSearch && (log?.query || "") !== query.trim());
  const lines = log?.lines || [];
  const groupedSources = useMemo(() => groupLogSources(sources), [sources]);
  const matching = useMemo(() => {
    if (onSearch || !query.trim()) return lines;
    const needle = query.toLowerCase();
    return lines.filter((line) => line.toLowerCase().includes(needle));
  }, [lines, query, onSearch]);

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
      {sources.length && onKeyChange ? (
        <label className="field log-source-select">
          <span>Log source</span>
          <select aria-label="Workflow stage or rule log" value={activeKey || ""} onChange={(event) => onKeyChange(event.target.value)}>
            {groupedSources.map((group) => (
              <optgroup key={group.label} label={group.label}>
                {group.items.map((source) => <option key={source.key} value={source.key}>{source.label}</option>)}
              </optgroup>
            ))}
          </select>
        </label>
      ) : (
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
      )}
      <label className="search-field">
        <Search size={15} />
        <span className="sr-only">Search logs</span>
        <input aria-label="Search logs" maxLength={256} value={query} placeholder={onSearch ? "Search file content" : "Search loaded excerpt"} onChange={(event) => setQuery(event.target.value)} />
      </label>
      {searching ? <p className="muted">Searching log content… Previous result remains visible.</p> : query ? <p className="muted">{log?.match_count ?? matching.length} matching lines · showing {matching.length}{log?.search_complete === false ? " · Scan limit reached; results are incomplete" : ""}</p> : <p className="muted">Latest log excerpt{log?.truncated ? " (truncated)" : ""}. {onSearch ? "Search checks file content, not just these lines." : "Search filters this excerpt only."}</p>}
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

function groupLogSources(sources: RunLogIndexItem[]): Array<{label: string; items: RunLogIndexItem[]}> {
  const failed = sources.filter((item) => item.sample_id && ["failed", "fail", "error"].includes(String(item.status || "").toLowerCase()));
  const current = sources.filter((item) => ["running", "started"].includes(String(item.status || "").toLowerCase()));
  const workflow = sources.filter((item) => !item.rule && !item.sample_id);
  const used = new Set([...failed, ...current, ...workflow].map((item) => item.key));
  const other = sources.filter((item) => !used.has(item.key));
  return [
    {label: "Failed sample logs", items: failed},
    {label: "Current step logs", items: current},
    {label: "Workflow stdout/stderr", items: workflow},
    {label: "Other rule logs", items: other},
  ].filter((group) => group.items.length > 0);
}

export function preferredLogSource(
  sources: RunLogIndexItem[],
  runStatus?: string | null,
  currentStep?: string | null,
): RunLogIndexItem | undefined {
  const failed = sources.filter((item) => item.sample_id && ["failed", "fail", "error"].includes(String(item.status || "").toLowerCase()));
  return failed.find((item) => item.stream === "stderr")
    || failed[0]
    || sources.find((item) => item.rule === currentStep)
    || sources.find((item) => item.stream === "stderr" && ["failed", "fail", "error", "terminated"].includes(String(runStatus || "").toLowerCase()))
    || sources[0];
}
