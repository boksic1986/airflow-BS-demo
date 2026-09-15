import {afterEach, expect, it, vi} from 'vitest';
import {listIncompleteWgsSubmissions} from './api';

afterEach(() => vi.unstubAllGlobals());

it('loads paginated submission summaries without per-run detail requests', async () => {
  const paths: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost');
    paths.push(url.pathname);
    if (url.pathname !== '/api/wgs/submissions/incomplete') throw new Error('Unexpected detail/list request');
    const offset = Number(url.searchParams.get('offset'));
    const ids = offset === 0 ? Array.from({length: 100}, (_, n) => `S${n}`) : ['S100'];
    return new Response(JSON.stringify({items: ids.map(analysis_id => ({analysis_id, pipeline:'wgs', status:'running', attempt:1, params:{submission_phase:'config_review'}})), total:101}), {status:200, headers:{'Content-Type':'application/json'}});
  }));
  const result = await listIncompleteWgsSubmissions();
  expect(result).toHaveLength(101);
  expect(result[100].analysis_id).toBe('S100');
  expect(paths).toEqual(['/api/wgs/submissions/incomplete', '/api/wgs/submissions/incomplete']);
});
