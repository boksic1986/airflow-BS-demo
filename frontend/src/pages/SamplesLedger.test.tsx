import '@testing-library/jest-dom';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {vi} from 'vitest';
import {SamplesPage} from './SamplesPage';
import * as api from '../api';

vi.mock('../api', () => ({listSampleReferences: vi.fn(), listSampleReferenceSources: vi.fn(), listSampleReferenceOperations: vi.fn(), listSamplesResource: vi.fn()}));
const row = {source_id: 'source', record_key: 'a'.repeat(64), sample_id: 'SYNTHETIC', family_id: 'F1',
  origin_batch: 'BATCH-A', sequencing_batch: 'SEQ-X', pending: true, present_in_latest_complete: true,
  reason_codes: ['sequencing_batch_missing'], needs_review: false, sync_status: 'ready' as const};
const page = (items: unknown[]) => ({items, total: items.length, limit: 25, offset: 0});
beforeEach(() => {
  vi.mocked(api.listSampleReferences).mockResolvedValue(page([row]) as api.Page<api.SampleReference>);
  vi.mocked(api.listSampleReferenceSources).mockResolvedValue(page([]) as api.Page<api.SampleReferenceSource>);
  vi.mocked(api.listSampleReferenceOperations).mockResolvedValue(page([]) as api.Page<api.SampleReferenceOperation>);
});
afterEach(() => {cleanup(); vi.clearAllMocks();});
function open() {render(<MemoryRouter initialEntries={['/samples?view=ledger']}><SamplesPage /></MemoryRouter>);}

it('requests current pending and uses Sample table and status badge', async () => {
  open();
  const sample = await screen.findByText('SYNTHETIC');
  expect(api.listSampleReferences).toHaveBeenCalledWith(expect.objectContaining({pending: true}));
  expect(sample.closest('table')).toHaveClass('sample-resource-table');
  expect(screen.getByText('Pending').closest('.status-badge')).not.toBeNull();
  expect(screen.getByText('缺少上机批次')).toBeInTheDocument();
  expect(screen.getByRole('columnheader', {name: '来源分析批次'})).toBeInTheDocument();
  expect(screen.queryByText('Last good / sync')).not.toBeInTheDocument();
  expect(screen.queryByText('Origin → target')).not.toBeInTheDocument();
});

it('keeps removed records accessible in history without inventing a receiving batch', async () => {
  open();
  await screen.findByText('SYNTHETIC');
  vi.mocked(api.listSampleReferences).mockResolvedValue(page([{...row, pending: false, present_in_latest_complete: false}]) as api.Page<api.SampleReference>);
  fireEvent.click(screen.getByRole('button', {name: '历史记录'}));
  expect(await screen.findByText('已移出待交接，接收批次未确认')).toBeInTheDocument();
  expect(screen.queryByText(/→/)).not.toBeInTheDocument();
});

it.each(['selected', 'consumed'] as const)('labels %s only according to its receipt', async role => {
  vi.mocked(api.listSampleReferenceOperations).mockResolvedValue(page([{
    operation_id: 'op', sequence: 1, mode: 'unknown', source_id: 'source', producer_commit: 'unknown',
    logical_transaction_time_semantics: 'unknown', links_total: 1, links_truncated: false,
    links: [{role, record_key: row.record_key, destination_batch: 'BATCH-B', reason_codes: []}],
  }]) as api.Page<api.SampleReferenceOperation>);
  open();
  await screen.findByText('SYNTHETIC');
  fireEvent.click(screen.getByRole('button', {name: '查看详情'}));
  await waitFor(() => expect(screen.getByText(role === 'selected' ? '已纳入 BATCH-B' : '已交接至 BATCH-B')).toBeInTheDocument());
  expect(screen.queryByText(role === 'selected' ? '已交接至 BATCH-B' : '已纳入 BATCH-B')).not.toBeInTheDocument();
});

it('keeps sync failure visible and replaces unclassified reason with safe text', async () => {
  vi.mocked(api.listSampleReferences).mockResolvedValue(page([{...row, sync_status: 'error', reason_codes: ['unrecognized_private_text']}]) as api.Page<api.SampleReference>);
  open();
  await screen.findByText('SYNTHETIC');
  expect(screen.getByRole('alert')).toHaveTextContent('交接来源同步异常');
  expect(screen.getByText('待核对原因')).toBeInTheDocument();
  expect(screen.queryByText('unrecognized_private_text')).not.toBeInTheDocument();
});
