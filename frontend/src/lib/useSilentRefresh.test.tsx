import {act, renderHook} from '@testing-library/react';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {useSilentRefresh} from './useSilentRefresh';

describe('silent refresh', () => {
  beforeEach(() => { vi.useFakeTimers(); Object.defineProperty(document, 'visibilityState', {configurable: true, value: 'visible'}); });
  afterEach(() => { vi.useRealTimers(); });
  it('polls visible pages at 10 seconds and backs off without clearing content', async () => {
    let calls = 0;
    const request = async () => { calls++; if (calls === 2) throw new Error('offline'); };
    const {result} = renderHook(() => useSilentRefresh(request, 'route'));
    await act(async () => {});
    expect(result.current.loading).toBe(false);
    await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    expect(calls).toBe(2);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('offline');
    await act(async () => { await vi.advanceTimersByTimeAsync(19999); });
    expect(calls).toBe(2);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(calls).toBe(3);
    expect(result.current.error).toBeNull();
  });
  it('never overlaps requests and invalidates an old route response', async () => {
    let finish: (() => void) | undefined;
    const published: string[] = [];
    let calls = 0;
    const {rerender} = renderHook(({route}) => useSilentRefresh(async ({isCurrent}) => {
      calls++;
      if (route === 'old') await new Promise<void>((resolve) => { finish = resolve; });
      if (isCurrent()) published.push(route);
    }, route), {initialProps: {route: 'old'}});
    await act(async () => { await vi.advanceTimersByTimeAsync(30000); });
    expect(calls).toBe(1);
    rerender({route: 'new'});
    await act(async () => { finish?.(); });
    expect(published).toEqual(['new']);
  });
  it('polls hidden pages at 60 seconds and refreshes immediately on return', async () => {
    const request = vi.fn(async () => {});
    renderHook(() => useSilentRefresh(request, 'route'));
    await act(async () => {});
    await act(async () => {
      Object.defineProperty(document, 'visibilityState', {configurable: true, value: 'hidden'});
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(59000);
    });
    expect(request).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(request).toHaveBeenCalledTimes(2);
    await act(async () => {
      Object.defineProperty(document, 'visibilityState', {configurable: true, value: 'visible'});
      document.dispatchEvent(new Event('visibilitychange'));
    });
    expect(request).toHaveBeenCalledTimes(3);
  });
});
