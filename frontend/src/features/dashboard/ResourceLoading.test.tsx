import '@testing-library/jest-dom';
import {render, screen} from '@testing-library/react';
import {DashboardResourcePanels} from './DashboardResourcePanels';
import type {PlatformResourcesResponse} from '../../api';

const base = {resourceTab: 'all' as const, overview: null, rows: [], onResourceTabChange: () => {}};

it('does not diagnose missing telemetry while the first resource request is pending', () => {
  render(<DashboardResourcePanels {...base} resources={null} loading error={null} />);
  expect(screen.getAllByRole('status').length).toBeGreaterThan(0);
  expect(screen.queryByText(/Node metrics are not available/)).not.toBeInTheDocument();
  expect(screen.queryByText(/SFS metrics are not available/)).not.toBeInTheDocument();
  expect(screen.queryByText(/SFS I\/O history is not available/)).not.toBeInTheDocument();
  expect(screen.queryByText('unavailable')).not.toBeInTheDocument();
});

it('reports a failed first request instead of an empty collector', () => {
  render(<DashboardResourcePanels {...base} resources={null} loading={false} error="Network request failed" />);
  expect(screen.getByRole('alert')).toHaveTextContent('Network request failed');
  expect(screen.queryByText(/Node metrics are not available/)).not.toBeInTheDocument();
  expect(screen.queryByText(/SFS metrics are not available/)).not.toBeInTheDocument();
});

it('retains real telemetry during a refresh failure', () => {
  const resources: PlatformResourcesResponse = {status: 'healthy', updated_at: '2026-09-14T16:30:00Z', items: [
    {resource_key: 'node-96', resource_type: 'node', display_name: 'node-96', status: 'healthy',
      source_updated_at: '2026-09-14T16:30:00Z', current: {cpu_used_percent: 17}, history: []},
  ]};
  render(<DashboardResourcePanels {...base} resources={resources} loading={false} error="Network request failed" />);
  expect(screen.getByText('17.0%')).toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('Network request failed');
});

it('only reports no telemetry after a successful empty response', () => {
  render(<DashboardResourcePanels {...base} resources={{status: 'stale', updated_at: '2026-09-14T16:30:00Z', items: []}} loading={false} error={null} />);
  expect(screen.getByText(/Node metrics are not available/)).toBeInTheDocument();
  expect(screen.getByText(/SFS metrics are not available/)).toBeInTheDocument();
});
