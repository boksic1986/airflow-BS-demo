import {act, renderHook} from '@testing-library/react';
import {useState} from 'react';
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
  it('starts a new scope without waiting for an old request that never returns', async () => {
    const calls: string[] = [];
    const published: string[] = [];
    let oldSignal: AbortSignal | undefined;
    const {result, rerender} = renderHook(({route}) => useSilentRefresh(async (context) => {
      calls.push(route);
      if (route === 'old') {
        oldSignal = (context as typeof context & {signal?: AbortSignal}).signal;
        await new Promise<void>(() => {});
      }
      if (context.isCurrent()) published.push(route);
    }, route), {initialProps: {route: 'old'}});
    await act(async () => {});

    rerender({route: 'new'});
    await act(async () => {});
    expect(calls).toEqual(['old', 'new']);
    expect(oldSignal?.aborted).toBe(true);
    expect(published).toEqual(['new']);
    expect(result.current.loading).toBe(false);
  });
  it('keeps the current controller and loading state after a late old finally', async () => {
    const calls: string[] = [];
    const published: string[] = [];
    const signals: Record<string, AbortSignal | undefined> = {};
    let finishOld: (() => void) | undefined;
    const {result, rerender} = renderHook(({route}) => useSilentRefresh(async (context) => {
      calls.push(route);
      signals[route] = (context as typeof context & {signal?: AbortSignal}).signal;
      if (route === 'old') await new Promise<void>((resolve) => { finishOld = resolve; });
      if (route === 'new') await new Promise<void>(() => {});
      if (context.isCurrent()) published.push(route);
    }, route), {initialProps: {route: 'old'}});
    await act(async () => {});
    rerender({route: 'new'});
    await act(async () => {});
    expect(calls).toEqual(['old', 'new']);

    await act(async () => { finishOld?.(); });
    expect(published).toEqual([]);
    expect(result.current.loading).toBe(true);
    expect(signals.new?.aborted).toBe(false);
    await act(async () => { window.dispatchEvent(new Event('focus')); });
    expect(calls).toEqual(['old', 'new']);

    rerender({route: 'third'});
    await act(async () => {});
    expect(signals.new?.aborted).toBe(true);
    expect(published).toEqual(['third']);
    expect(result.current.loading).toBe(false);
  });
  it('keeps loaded content visible while a new scope is pending and fails', async () => {
    let failNew: ((failure: Error) => void) | undefined;
    let newInitial: boolean | undefined;
    const {result, rerender} = renderHook(({route}) => {
      const [content, setContent] = useState('');
      const refresh = useSilentRefresh(async ({isCurrent, initial}) => {
        if (route === 'new') {
          newInitial = initial;
          await new Promise<void>((_resolve, reject) => { failNew = reject; });
        }
        if (isCurrent()) setContent(`${route} content`);
      }, route);
      return {...refresh, visible: refresh.loading ? 'Loading...' : content};
    }, {initialProps: {route: 'old'}});
    await act(async () => {});
    expect(result.current.visible).toBe('old content');

    rerender({route: 'new'});
    await act(async () => {});
    expect(newInitial).toBe(false);
    expect(result.current.loading).toBe(false);
    expect(result.current.visible).toBe('old content');
    await act(async () => { failNew?.(new Error('offline')); });
    expect(result.current.error).toBe('offline');
    expect(result.current.loading).toBe(false);
    expect(result.current.visible).toBe('old content');
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
