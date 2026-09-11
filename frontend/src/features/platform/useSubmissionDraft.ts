import {useEffect, useState} from 'react';
import {useSession} from '../auth/SessionContext';

// Tab-local and account-scoped; no credentials or sample table content.
export function useSubmissionDraft<T>(pipeline: string, field: string, initial: T) {
  const {user} = useSession();
  const key = `submission-v1:${user?.username || 'anonymous'}:${pipeline}:${field}`;
  const [value, setValue] = useState<T>(() => {
    try {const raw = sessionStorage.getItem(key); const parsed:unknown = raw ? JSON.parse(raw) : initial; return typeof parsed === typeof initial ? parsed as T : initial;} catch {return initial;}
  });
  useEffect(() => {try {sessionStorage.setItem(key, JSON.stringify(value));} catch {/* Storage can be disabled. */}}, [key, value]);
  return [value, setValue] as const;
}
