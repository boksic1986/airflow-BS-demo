import '@testing-library/jest-dom/vitest';
import {act, cleanup, fireEvent, render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import App from './App';

afterEach(() => {cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); window.history.pushState({}, '', '/');});

it('serializes preparation refreshes and shows the next stage after a two-second refresh', async () => {
  vi.useFakeTimers();
  Object.defineProperty(document, 'visibilityState', {configurable: true, value: 'visible'});
  window.history.pushState({}, '', '/submit?pipeline=wgs&analysis_id=SYNTH');
  let phase = 'preparing_sampleinfo';
  let calls = 0;
  let pending: (() => void) | undefined;
  const json = (data: unknown) => new Response(JSON.stringify(data), {status: 200});
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), 'http://localhost').pathname;
    if (path === '/api/auth/me') return json({username: 'operator', role: 'operator'});
    if (path === '/api/platform/capabilities') return json({environment: 'test', deployed_pipelines: ['wgs'], pipelines: [{id: 'wgs', display_name: 'WGS', dag_id: 'bio_wgs', enabled: true, submit_enabled: true, capabilities: ['submit'], execution_targets: ['cce']}]});
    if (path === '/api/wgs/release') return json({source_commit: 'synthetic', execution_enabled: true, runtime_adapter_enabled: true, submission_options: {defaults: {algo: 'sentieon', use_reference: 'ref'}, callers: [{value: 'sentieon'}], reference_values: ['ref', 'no']}});
    if (path === '/api/runs/SYNTH') {
      calls++;
      const captured = phase;
      if (calls === 2) await new Promise<void>(resolve => {pending = resolve;});
      return json({analysis_id: 'SYNTH', pipeline: 'wgs', attempt: 1, status: 'running', params: {submission_phase: captured, use_reference: 'ref'}});
    }
    return json({items: [], total: 0});
  }));
  render(<App />);
  await act(async () => {await vi.advanceTimersByTimeAsync(0);});
  expect(screen.getByText('Preparing sample information')).toBeInTheDocument();
  await act(async () => {await vi.advanceTimersByTimeAsync(10000);});
  expect(calls).toBe(2);
  await act(async () => {pending?.(); await vi.advanceTimersByTimeAsync(0);});
  phase = 'config_review';
  await act(async () => {await vi.advanceTimersByTimeAsync(2000);});
  expect(screen.getByRole('button', {name: 'Confirm configuration'})).toBeInTheDocument();
  const reference = screen.getByRole('combobox', {name: 'Use reference'});
  fireEvent.change(reference, {target: {value: 'no'}});
  await act(async () => {await vi.advanceTimersByTimeAsync(10000);});
  expect(reference).toHaveValue('no');
});
