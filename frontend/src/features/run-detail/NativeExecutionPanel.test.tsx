import '@testing-library/jest-dom/vitest';
import {cleanup, fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {NativeExecutionPanel} from './NativeExecutionPanel';
import {getNativeRunView} from '../../api';

vi.mock('../../api', () => ({getNativeRunView: vi.fn()}));
afterEach(() => {cleanup(); vi.clearAllMocks();});
const detail = {analysis_id: 'SYN_RUN', pipeline: 'wgs', status: 'running', submitted_by: 'operator', params: {native_monitor_only: true}};
const executions = [
  {execution_id: 'E2', generation: 2, attempt: 1, status: 'running', registered_by: 'operator', sample_count: 1},
  {execution_id: 'E1', generation: 1, attempt: 1, status: 'success', registered_by: 'operator', sample_count: 1},
];
function response(execution = 'E2') {
  return {analysis_id: 'SYN_RUN', current_execution_id: 'E2', executions, history_total: 2, history_offset: 0,
    selected: executions.find(row => row.execution_id === execution), samples: [{data_id: execution === 'E2' ? 'NEW' : 'OLD', sample_id: execution === 'E2' ? 'RENAMED' : 'ORIGINAL', family_id: 'F'}],
    sample_total: 1, rules: [], rule_total: 0, rules_incomplete: false, log: null, evidence_health: 'available',
    qc: {scope: 'run_latest', health: 'available', updated_at: '2026-09-16T01:00:00Z', items: [{sample_id: 'QC_LATEST', qc_status: 'pass', qc_metrics: {average_depth: '41'}}]}, offset: 0, limit: 25};
}

it('defaults to current scope, switches history, and keeps QC run-wide without cloud actions', async () => {
  vi.mocked(getNativeRunView).mockImplementation(async (_id, options) => response(options.execution_id || 'E2') as never);
  render(<NativeExecutionPanel detail={detail} />);
  expect(await screen.findByText('RENAMED')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Execution'), {target: {value: 'E1'}});
  expect(await screen.findByText('ORIGINAL')).toBeInTheDocument();
  expect(screen.queryByText('RENAMED')).toBeNull();
  fireEvent.click(screen.getByRole('tab', {name: 'QC'}));
  expect(await screen.findByText('QC_LATEST')).toBeInTheDocument();
  expect(screen.getByText(/本 run 最新 QC/)).toBeInTheDocument();
  expect(screen.getByText('41')).toBeInTheDocument();
  expect(screen.queryByRole('button', {name: /Submit|Cancel|Resume|SFS|repair/i})).toBeNull();
});

it('does not display the previous execution while a new selection is loading', async () => {
  let resolveOld!: (value: never) => void;
  vi.mocked(getNativeRunView).mockImplementation(async (_id, options) => options.execution_id === 'E1'
    ? new Promise(resolve => {resolveOld = resolve;}) : response() as never);
  render(<NativeExecutionPanel detail={detail} />);
  await screen.findByText('RENAMED');
  fireEvent.change(screen.getByLabelText('Execution'), {target: {value: 'E1'}});
  await waitFor(() => expect(resolveOld).toBeDefined());
  expect(screen.queryByText('RENAMED')).toBeNull();
  resolveOld(response('E1') as never);
  const table = await screen.findByRole('table', {name: 'Execution samples'});
  expect(await within(table).findByText('ORIGINAL')).toBeInTheDocument();
});

it('keeps the log search input mounted across a server search refresh', async () => {
  vi.mocked(getNativeRunView).mockImplementation(async (_id, options) => ({...response(),
    log: {stream: 'stdout', lines: options.query ? ['mapping matched'] : ['initial log'], query: options.query || '', truncated: false}}) as never);
  render(<NativeExecutionPanel detail={detail} />);
  await screen.findByText('RENAMED');
  fireEvent.click(screen.getByRole('tab', {name: 'Logs'}));
  const search = await screen.findByRole('textbox', {name: 'Search logs'});
  fireEvent.change(search, {target: {value: 'mapping'}});
  await screen.findByText('matched', {exact: false});
  expect(search).toHaveValue('mapping');
});
