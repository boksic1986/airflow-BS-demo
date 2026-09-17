import '@testing-library/jest-dom/vitest';
import {cleanup, fireEvent, render, screen, within} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import {NativeExecutionPanel} from './NativeExecutionPanel';
import {getNativeRunView} from '../../api';

vi.mock('../../api', () => ({getNativeRunView: vi.fn()}));
afterEach(() => {cleanup(); vi.clearAllMocks();});
const detail = {analysis_id: 'SYN_RUN', pipeline: 'wgs', status: 'running', submitted_by: 'operator', params: {native_monitor_only: true, execution_target: 'node-97'}};
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

it('shows current scope and latest QC without technical history or cloud actions', async () => {
  vi.mocked(getNativeRunView).mockImplementation(async (_id, options) => response(options.execution_id || 'E2') as never);
  render(<NativeExecutionPanel detail={detail} />);
  expect(await screen.findByText('RENAMED')).toBeInTheDocument();
  expect(screen.queryByLabelText('Execution')).toBeNull();
  expect(screen.queryByText('执行历史与技术信息')).toBeNull();
  fireEvent.click(screen.getByRole('tab', {name: 'QC'}));
  expect(await screen.findByText('QC_LATEST')).toBeInTheDocument();
  expect(screen.getByText(/本 run 最新 QC/)).toBeInTheDocument();
  expect(screen.getByText('41')).toBeInTheDocument();
  expect(screen.queryByRole('button', {name: /Submit|Cancel|Resume|SFS|repair/i})).toBeNull();
});

it('reuses phase summaries without CCE orchestration modules', async () => {
  vi.mocked(getNativeRunView).mockResolvedValue({...response(), phase_summaries: [
    {phase:'Mapping',status:'running',total:3,running:3,success:0,failed:0,canceled:0},
    {phase:'FASTQ QC',status:'success',total:3,running:0,success:3,failed:0,canceled:0},
  ]} as never);
  render(<NativeExecutionPanel detail={detail} />);
  await screen.findByText('RENAMED');
  expect(screen.getByText('WGS · node97')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', {name:'Rules'}));
  expect(await screen.findByText('Pipeline phases')).toBeInTheDocument();
  expect(screen.getByRole('table', {name:'Pipeline phase summary'})).toBeInTheDocument();
  expect(screen.getByText('3/3 jobs complete')).toBeInTheDocument();
  expect(screen.queryByText('Workflow execution path')).toBeNull();
  expect(screen.queryByText('Airflow project tasks')).toBeNull();
});

it('keeps the log search input mounted across a server search refresh', async () => {
  vi.mocked(getNativeRunView).mockImplementation(async (_id, options) => ({...response(),
    log: {stream: 'stdout', lines: options.query ? ['mapping matched'] : ['initial log'], query: options.query || '', truncated: false}}) as never);
  render(<NativeExecutionPanel detail={detail} />);
  await screen.findByText('RENAMED');
  fireEvent.click(screen.getByRole('tab', {name: 'Logs'}));
  const search = await screen.findByRole('textbox', {name: 'Search logs'});
  expect(screen.getByRole('option', {name: 'Snakemake log'})).toBeInTheDocument();
  fireEvent.change(search, {target: {value: 'mapping'}});
  await screen.findByText('matched', {exact: false});
  expect(search).toHaveValue('mapping');
});

it('shows percentage progress and plain rules without expansion controls', async () => {
  vi.mocked(getNativeRunView).mockResolvedValue({...response(),
    progress: {available: true, percent: 25, completed_units: 2, total_units: 8, observed_rules: 3},
    rules: [{rule: 'pre_process_mapping', rule_instance_id: 'E2:3', job_id: '3',
      snakemake_jobid: '3', phase: 'Mapping', status: 'running', sample_id: 'RENAMED',
      source_line: 8, message: 'Native log line 8', timing_provenance: 'native_log_local_time'}], rule_total: 1} as never);
  render(<NativeExecutionPanel detail={detail} />);
  expect(await screen.findByRole('progressbar')).toHaveAttribute('aria-valuenow', '25');
  fireEvent.click(screen.getByRole('tab', {name: 'Rules'}));
  const table = await screen.findByRole('table', {name: 'Pipeline rule instances'});
  expect(within(table).queryByRole('button', {name: 'Details for pre_process_mapping'})).toBeNull();
  expect(within(table).getByText('pre_process_mapping')).toBeInTheDocument();
  expect(within(table).getByText('Native log line 8')).toBeInTheDocument();
});
