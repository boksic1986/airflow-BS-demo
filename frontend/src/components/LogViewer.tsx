import {Copy, Download, Search} from "lucide-react";
import {type ReactNode, useEffect, useMemo, useRef, useState} from "react";

import type {LogStream, RunLog, RunLogIndexItem, RunLogArchive} from "../api";

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
  archive,
}: {
  stream: LogStream;
  onStreamChange: (stream: LogStream) => void;
  log: RunLog | null;
  error: string | null;
  sources?: RunLogIndexItem[];
  activeKey?: string | null;
  onKeyChange?: (key: string) => void;
  onSearch?: (query: string, matchIndex: number) => void;
  archive?: RunLogArchive;
}) {
  const [query, setQuery] = useState("");
  const [matchIndex, setMatchIndex] = useState(0);
  const viewer = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!onSearch) return;
    const timer = setTimeout(() => onSearch(query.trim(), 0), 350);
    return () => clearTimeout(timer);
  }, [query, onSearch]);
  const searching = Boolean(onSearch && ((log?.query || "") !== query.trim() || (query.trim() && (log?.match_index ?? 0) !== matchIndex)));
  const lines = log?.lines || [];
  const groupedSources = useMemo(() => groupLogSources(sources), [sources]);
  const matchingLines = useMemo(() => {
    if (!query.trim()) return [];
    const needle = query.trim().toLowerCase();
    return lines.flatMap((line, index) => line.toLowerCase().includes(needle) ? [index] : []);
  }, [lines, query]);
  const matchCount = onSearch ? log?.match_count ?? 0 : matchingLines.length;
  const activeLine = onSearch ? log?.match_line : matchingLines[matchIndex];
  useEffect(() => {
    if (searching || !query.trim() || activeLine == null) return;
    const container = viewer.current;
    const target = container?.children[activeLine] as HTMLElement | undefined;
    if (container && target) container.scrollTop += target.getBoundingClientRect().top - container.getBoundingClientRect().top - container.clientHeight / 3;
  }, [log, activeLine, searching, query]);
  function navigate(delta: number) {
    const next = Math.max(0, Math.min(matchCount - 1, matchIndex + delta));
    setMatchIndex(next);
    onSearch?.(query.trim(), next);
  }

  async function copyVisible() {
    await navigator.clipboard?.writeText(lines.join("\n"));
  }

  return (
    <section className="panel">
      <div className="section-heading split">
        <h2>Logs</h2>
        {archive ? (archive.available && archive.url ? <a className="button ghost" href={archive.url} download><Download size={15} /> Download logs</a>
          : <button className="button ghost" type="button" disabled><Download size={15} /> Download logs</button>) : <button className="button ghost" type="button" onClick={() => void copyVisible()} aria-label="Copy visible log excerpt">
          <Copy size={15} />
          Copy
        </button>}
      </div>
      {archive && !archive.available ? <p className="muted">{archive.reason || '日志包尚未就绪。'}</p> : null}
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
      <div className="log-search-toolbar"><label className="search-field">
        <Search size={15} />
        <span className="sr-only">Search logs</span>
        <input aria-label="Search logs" maxLength={256} value={query} placeholder={onSearch ? "Search file content" : "Search loaded excerpt"} onChange={(event) => { setQuery(event.target.value); setMatchIndex(0); }} />
      </label>
      <span className="muted" aria-live="polite">{query.trim() && !searching ? `${activeLine != null ? matchIndex + 1 : 0} / ${matchCount}` : "—"}</span>
      <button className="button ghost" type="button" disabled={searching || !query.trim() || matchIndex <= 0} onClick={() => navigate(-1)}>上一个</button>
      <button className="button ghost" type="button" disabled={searching || !query.trim() || matchIndex + 1 >= matchCount} onClick={() => navigate(1)}>下一个</button>
      </div>
      {searching ? <p className="muted">Searching log content… Previous result remains visible.</p> : query.trim() ? <p className="muted">{matchCount ? "保留匹配位置的连续上下文" : "未找到匹配内容"}{log?.search_complete === false ? " · 已达到扫描上限，结果不完整" : ""}</p> : <p className="muted">Latest log excerpt{log?.truncated ? " (truncated)" : ""}. {onSearch ? "Search checks file content, not just these lines." : "Search locates text within this excerpt."}</p>}
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      <div ref={viewer} className="log-viewer" aria-label={`${stream} log`}>
        {lines.length ? (
          lines.map((line, index) => (
            <div className={`log-line${/error|exception|failed|traceback/i.test(line) ? " error-line" : ""}${query.trim() && index === activeLine ? " log-search-current" : ""}`} key={`${line}-${index}`}>
              {highlightMatches(line, onSearch ? log?.query || "" : query.trim())}
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

function highlightMatches(line: string, query: string): ReactNode {
  if (!query) return line;
  const parts: ReactNode[] = [];
  const haystack = line.toLowerCase();
  const needle = query.toLowerCase();
  let cursor = 0;
  let index = haystack.indexOf(needle);
  while (index !== -1) {
    parts.push(line.slice(cursor, index));
    parts.push(<mark className="log-search-match" key={index}>{line.slice(index, index + query.length)}</mark>);
    cursor = index + query.length;
    index = haystack.indexOf(needle, cursor);
  }
  parts.push(line.slice(cursor));
  return parts;
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
