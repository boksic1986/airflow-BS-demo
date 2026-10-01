import {useCallback, useEffect, useRef, useState} from 'react';
import {errorMessage} from './errors';

export type RefreshContext = {isCurrent: () => boolean; initial: boolean; signal: AbortSignal};

/** One in-flight task per current scope, with cancellation and stale-route fencing. */
export function useSilentRefresh(task: (context: RefreshContext) => Promise<unknown>, key: string, enabled = true, intervalMs = 10000) {
  const taskRef = useRef(task);
  taskRef.current = task;
  const keyRef = useRef(key);
  keyRef.current = key;
  const trigger = useRef<() => Promise<void>>(async () => {});
  const completed = useRef(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) { trigger.current = async () => {}; return; }
    let alive = true;
    let timer: number | undefined;
    let failures = 0;
    let scheduled = false;
    let controller: AbortController | null = null;
    const isCurrent = () => alive && keyRef.current === key;
    setError(null);
    const delay = () => Math.max(document.visibilityState === 'hidden' ? 60000 : intervalMs,
      failures ? Math.min(60000, 20000 * 2 ** (failures - 1)) : 0);
    const schedule = () => {
      window.clearTimeout(timer);
      if (isCurrent()) timer = window.setTimeout(() => { void run(); }, delay());
    };
    const run = async () => {
      if (!isCurrent() || scheduled) return;
      scheduled = true;
      window.clearTimeout(timer);
      const requestController = new AbortController();
      controller = requestController;
      try {
        await Promise.resolve().then(() => {
          if (!isCurrent() || requestController.signal.aborted) return;
          return taskRef.current({isCurrent, initial: !completed.current, signal: requestController.signal});
        });
        if (isCurrent()) { failures = 0; setError(null); }
      } catch (failure) {
        if (isCurrent()) { failures++; setError(errorMessage(failure)); }
      } finally {
        if (controller === requestController) controller = null;
        if (isCurrent()) { completed.current = true; setLoading(false); }
        scheduled = false;
        schedule();
      }
    };
    trigger.current = run;
    const visibility = () => {
      if (document.visibilityState === 'visible') void run();
      else schedule();
    };
    const focus = () => { if (document.visibilityState !== 'hidden') void run(); };
    document.addEventListener('visibilitychange', visibility);
    window.addEventListener('focus', focus);
    void run();
    return () => {
      alive = false;
      controller?.abort();
      window.clearTimeout(timer);
      if (trigger.current === run) trigger.current = async () => {};
      document.removeEventListener('visibilitychange', visibility);
      window.removeEventListener('focus', focus);
    };
  }, [key, enabled, intervalMs]);
  const refresh = useCallback(() => trigger.current(), []);
  return {loading, error, refresh};
}
