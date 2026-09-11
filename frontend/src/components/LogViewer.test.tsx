import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {describe, expect, it, vi} from 'vitest';
import {LogViewer} from './LogViewer';

describe('server log search', () => {
  it('requests content search and labels tail-only versus incomplete results', async () => {
    const search = vi.fn();
    const {rerender} = render(<LogViewer stream="stdout" onStreamChange={() => {}} error={null}
      onSearch={search} log={{stream:'stdout', lines:['finished'], truncated:true}} />);
    expect(screen.getByText(/Latest log excerpt/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Search logs'), {target:{value:'fastp'}});
    await waitFor(() => expect(search).toHaveBeenLastCalledWith('fastp'));
    expect(screen.getByText(/Searching log content/)).toBeTruthy();
    rerender(<LogViewer stream="stdout" onStreamChange={() => {}} error={null} onSearch={search}
      log={{stream:'stdout',lines:['fastp earlier'],truncated:false,query:'fastp',match_count:1,search_complete:true}} />);
    expect(screen.getByText('fastp earlier')).toBeTruthy();
    expect(screen.getByText(/1 matching line/)).toBeTruthy();
  });
});
