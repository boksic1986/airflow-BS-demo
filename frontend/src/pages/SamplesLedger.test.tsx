import '@testing-library/jest-dom';
import {cleanup, fireEvent, render, screen, within} from '@testing-library/react';
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
  expect(screen.getByRole('tablist', {name: '样本流转范围'})).toHaveClass('tab-row');
  expect(screen.getByRole('tab', {name: '待纳入'})).toHaveAttribute('aria-selected', 'true');
  expect(sample.closest('table')).toHaveClass('sample-resource-table');
  expect(within(sample.closest('tr')!).getByText('待纳入').closest('.status-badge')).not.toBeNull();
  expect(screen.queryByText('缺少上机批次')).toBeNull();
  expect(screen.getByRole('columnheader', {name: '来源分析批次'})).toBeInTheDocument();
  expect(screen.queryByText('Last good / sync')).not.toBeInTheDocument();
  expect(screen.queryByText('Origin → target')).not.toBeInTheDocument();
});

it('keeps removed records accessible in history without inventing a receiving batch', async () => {
  open();
  await screen.findByText('SYNTHETIC');
  vi.mocked(api.listSampleReferences).mockResolvedValue(page([{...row, pending: false, present_in_latest_complete: false}]) as api.Page<api.SampleReference>);
  fireEvent.click(screen.getByRole('tab', {name: '纳入记录'}));
  expect(await screen.findByText('待关联')).toBeInTheDocument();
  expect(screen.queryByText(/→/)).not.toBeInTheDocument();
});

it.each(['selected', 'consumed'] as const)('separates %s status from the included batch', async role => {
  vi.mocked(api.listSampleReferences).mockResolvedValue(page([{...row,pending:false,present_in_latest_complete:false,
    latest_decision:{role,destination_batch:'BATCH-B',operation_id:'op',analysis_id:'RUN-B'}}]) as api.Page<api.SampleReference>);
  render(<MemoryRouter initialEntries={['/samples?view=ledger&ledger_scope=history']}><SamplesPage /></MemoryRouter>);
  const sample=await screen.findByText('SYNTHETIC');
  const cells=within(sample.closest('tr')!).getAllByRole('cell');
  expect(cells).toHaveLength(4);
  expect(cells[2]).toHaveTextContent(role==='selected' ? '已纳入' : '已交接');
  expect(cells[2]).not.toHaveTextContent('BATCH-B');
  expect(cells[2].querySelector('small')).toBeNull();
  expect(within(cells[3]).getByRole('link',{name:'BATCH-B'})).toHaveAttribute('href','/runs/RUN-B');
  expect(api.listSampleReferenceOperations).not.toHaveBeenCalled();
});

it('keeps sync failure visible and replaces unclassified reason with safe text', async () => {
  vi.mocked(api.listSampleReferences).mockResolvedValue(page([{...row, sync_status: 'error', reason_codes: ['unrecognized_private_text']}]) as api.Page<api.SampleReference>);
  open();
  await screen.findByText('SYNTHETIC');
  expect(screen.getByRole('alert')).toHaveTextContent('交接来源同步异常');
  expect(screen.queryByText('待核对原因')).toBeNull();
  expect(screen.queryByText('unrecognized_private_text')).not.toBeInTheDocument();
});
it('uses workflow names and removes detail controls and explanatory copy', async () => {
  open();
  await screen.findByText('SYNTHETIC');
  expect(screen.getByRole('tab',{name:'样本流转'})).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'样本流转'})).toBeInTheDocument();
  expect(screen.getByRole('columnheader',{name:'纳入批次'})).toBeInTheDocument();
  expect(screen.queryByRole('columnheader',{name:'详情'})).toBeNull();
  expect(screen.queryByRole('button',{name:'查看详情'})).toBeNull();
  expect(screen.queryByText(/当前待交接仅显示|包含当前与已移出记录|最近凭据/)).toBeNull();
});
