import {useCallback, useEffect, useRef, useState} from 'react';
import {errorMessage} from './errors';

export type RefreshContext = {isCurrent: () => boolean; initial: boolean};

/** One in-flight request per mounted consumer, with stale-route fencing. */
export function useSilentRefresh(task: (context: RefreshContext) => Promise<unknown>, key: string, enabled = true) {
  const taskRef = useRef(task);
  taskRef.current = task;
  const keyRef = useRef(key);
  keyRef.current = key;
  const pending = useRef<Promise<unknown> | null>(null);
  const trigger = useRef<() => Promise<void>>(async () => {});
  const completed = useRef(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    let timer: number | undefined;
    let failures = 0;
    let scheduled = false;
    const isCurrent = () => alive && keyRef.current === key;
    const delay = () => Math.max(document.visibilityState === 'hidden' ? 60000 : 10000,
      failures ? Math.min(60000, 20000 * 2 ** (failures - 1)) : 0);
    const schedule = () => {
      window.clearTimeout(timer);
      if (isCurrent()) timer = window.setTimeout(() => { void run(); }, delay());
    };
    const run = async () => {
      if (!isCurrent() || scheduled) return;
      scheduled = true;
      window.clearTimeout(timer);
      // A route change may leave a request in flight. Wait; never publish it.
      if (pending.current) await pending.current.catch(() => undefined);
      if (!isCurrent()) { scheduled = false; return; }
      const request = Promise.resolve().then(() => taskRef.current({isCurrent, initial: !completed.current}));
      pending.current = request;
      try {
        await request;
        if (isCurrent()) { failures = 0; setError(null); }
      } catch (failure) {
        if (isCurrent()) { failures++; setError(errorMessage(failure)); }
      } finally {
        if (pending.current === request) pending.current = null;
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
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', visibility);
      window.removeEventListener('focus', focus);
    };
  }, [key, enabled]);
  const refresh = useCallback(() => trigger.current(), []);
  return {loading, error, refresh};
}
