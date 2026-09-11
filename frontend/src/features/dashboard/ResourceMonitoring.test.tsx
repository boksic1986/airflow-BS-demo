import '@testing-library/jest-dom';
import {render, screen} from '@testing-library/react';
import {DashboardResourcePanels} from './DashboardResourcePanels';
import type {PlatformResourcesResponse} from '../../api';

it('shows known heavy occupancy independently of missing SFS and unknown waiting', () => {
  const resources = {status: 'stale', items: [], updated_at: '', resource_packages: {status: 'not_configured', reason: 'dedicated_billing_credentials_missing', items: [], updated_at: null, checked_at: null, source: 'Huawei Cloud BSS', interval_seconds: 3600}, heavy_slot: {
    pool: 'wgs-heavy-io', used: 11, limit: 25, waiting: null, mode: 'enforce', available: false,
    unit: 'heavy_work_job', fields: {used: {status: 'fresh'}, limit: {status: 'fresh'}, waiting: {status: 'unavailable', reason: 'waiting_snapshot_unavailable'}, mode: {status: 'fresh'}},
  }} as PlatformResourcesResponse;
  render(<DashboardResourcePanels resources={resources} resourceTab="all" overview={null} rows={[]} loading={false} error={null} onResourceTabChange={() => {}} />);
  expect(screen.getByText('11 / 25')).toBeInTheDocument();
  expect(screen.getByText(/waiting unavailable/)).toBeInTheDocument();
  expect(screen.getByText(/one grouped Job/)).toBeInTheDocument();
  expect(screen.queryByText(/0 waiting/)).not.toBeInTheDocument();
  expect(screen.getByText(/Resource package balances/)).toBeInTheDocument();
  expect(screen.getByText(/not_configured/)).toBeInTheDocument();
});

it('retains separately labelled stale package balances with original units and periods', () => {
  const resources: PlatformResourcesResponse = {status: 'stale', items: [], updated_at: '', resource_packages: {
    status: 'stale', reason: 'forbidden', source: 'Huawei Cloud BSS', interval_seconds: 3600,
    updated_at: '2026-09-12T00:00:00Z', checked_at: '2026-09-12T01:00:00Z',
    items: [{key: 'bss-a', category: 'cpu_hours', total: '100.25', remaining: '12.123456789012345678', unit: 'core-hours',
      period_start: '2026-09-01T00:00:00Z', period_end: '2026-10-01T00:00:00Z', expires_at: '2027-01-01T00:00:00Z', cycle: 'month', cycle_type: 'calendar'},
      {key: 'bss-b', category: 'memory_hours', total: '300', remaining: '250', unit: 'GiB-hours',
      period_start: '2026-09-01T00:00:00Z', period_end: '2026-10-01T00:00:00Z', expires_at: '2027-01-01T00:00:00Z', cycle: 'month', cycle_type: 'subscription'}],
  }};
  render(<DashboardResourcePanels resources={resources} resourceTab="all" overview={null} rows={[]} loading={false} error={null} onResourceTabChange={() => {}} />);
  expect(screen.getByText('stale · forbidden')).toBeInTheDocument();
  expect(screen.getByText('12.123456789012345678 / 100.25 core-hours remaining / total')).toBeInTheDocument();
  expect(screen.getByText('250 / 300 GiB-hours remaining / total')).toBeInTheDocument();
  expect(screen.getByText(/month · calendar/)).toBeInTheDocument();
  expect(screen.getByText(/month · subscription/)).toBeInTheDocument();
  expect(screen.queryByText(/262.123/)).not.toBeInTheDocument();
});

it('does not infer absent credentials from an unavailable API response', () => {
  render(<DashboardResourcePanels resources={null} resourceTab="all" overview={null} rows={[]} loading={false} error="timeout" onResourceTabChange={() => {}} />);
  expect(screen.queryByText(/not_configured/)).not.toBeInTheDocument();
  expect(screen.getByText(/cache_not_reported/)).toBeInTheDocument();
});
