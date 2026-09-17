import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {describe, expect, it, vi} from 'vitest';
import {LogViewer} from './LogViewer';

describe('server log search', () => {
  it('offers the complete archive instead of copying a visible excerpt in CCE mode', () => {
    const {rerender} = render(<LogViewer stream="stdout" onStreamChange={() => {}} error={null} log={null}
      archive={{available:true,url:'/api/runs/SYN/logs/archive?key=abc'}} />);
    expect(screen.queryByRole('button',{name:'Copy visible log excerpt'})).toBeNull();
    expect(screen.getByRole('link',{name:'Download logs'}).getAttribute('href')).toBe('/api/runs/SYN/logs/archive?key=abc');
    rerender(<LogViewer stream="stdout" onStreamChange={() => {}} error={null} log={null}
      archive={{available:false,reason:'日志包尚未就绪'}} />);
    expect(screen.getByRole('button',{name:'Download logs'}).hasAttribute('disabled')).toBe(true);
    expect(screen.getByText('日志包尚未就绪')).toBeTruthy();
  });
  it('requests content search and labels tail-only versus incomplete results', async () => {
    const search = vi.fn();
    const {rerender} = render(<LogViewer stream="stdout" onStreamChange={() => {}} error={null}
      onSearch={search} log={{stream:'stdout', lines:['finished'], truncated:true}} />);
    expect(screen.getByText(/Latest log excerpt/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Search logs'), {target:{value:'fastp'}});
    await waitFor(() => expect(search).toHaveBeenLastCalledWith('fastp', 0));
    expect(screen.getByText(/Searching log content/)).toBeTruthy();
    rerender(<LogViewer stream="stdout" onStreamChange={() => {}} error={null} onSearch={search}
      log={{stream:'stdout',lines:['before','fastp earlier','input: sample','output: result'],truncated:false,query:'fastp',match_count:2,match_index:0,match_line:1,search_complete:true}} />);
    expect(screen.getByLabelText('stdout log').textContent).toContain('fastp earlier');
    expect(screen.getByText('fastp').tagName).toBe('MARK');
    expect(screen.getByLabelText('stdout log').textContent).toContain('input: sample');
    expect(screen.getByText('1 / 2')).toBeTruthy();
    fireEvent.click(screen.getByRole('button',{name:'下一个'}));
    expect(search).toHaveBeenLastCalledWith('fastp', 1);
    rerender(<LogViewer stream="stdout" onStreamChange={() => {}} error={null} onSearch={search}
      log={{stream:'stdout',lines:['second fastp','context'],truncated:false,query:'fastp',match_count:2,match_index:1,match_line:0,search_complete:true}} />);
    fireEvent.click(screen.getByRole('button',{name:'上一个'}));
    expect(search).toHaveBeenLastCalledWith('fastp', 0);
  });
  it('highlights all literal case-insensitive matches without interpreting HTML or regex', () => {
    const {container} = render(<LogViewer stream="stdout" onStreamChange={() => {}} error={null}
      log={{stream:'stdout',lines:['<script>x</script> A.B a.b axb','keep context'],truncated:false}} />);
    fireEvent.change(screen.getByLabelText('Search logs'),{target:{value:'a.b'}});
    expect(Array.from(container.querySelectorAll('mark')).map(x=>x.textContent)).toEqual(['A.B','a.b']);
    expect(container.querySelector('script')).toBeNull();
    expect(screen.getByLabelText('stdout log').textContent).toContain('keep context');
  });
});
