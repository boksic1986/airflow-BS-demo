import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import {afterEach, expect, it, vi} from 'vitest';
import {ResumeStagePanel, monitorReconnectAvailable} from './ResumeStagePanel';
import * as api from '../../api';

afterEach(() => vi.restoreAllMocks());
it('requires explicit same-attempt confirmation and retains the idempotency key after an uncertain response', async () => {
  vi.spyOn(crypto,'randomUUID').mockImplementation(() => {throw new Error('insecure HTTP context');});
  const submit=vi.spyOn(api,'resumeStage').mockRejectedValueOnce(new Error('uncertain')).mockResolvedValue({analysis_id:'mock',attempt:1,stage:'step3_monitor',generation:2,action_id:'resume-mock',status:'queued'});
  render(<ResumeStagePanel analysisId="mock" attempt={1} stage="step3_monitor" canOperate onAccepted={() => undefined}/>);
  const button=screen.getByRole('button',{name:'继续当前阶段'});
  expect(button).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(button);
  await screen.findByRole('alert');
  fireEvent.click(button);
  await waitFor(() => expect(submit).toHaveBeenCalledTimes(2));
  expect(submit.mock.calls[0]).toEqual(submit.mock.calls[1]);
  expect(submit.mock.calls[0][1]).toMatchObject({attempt:1,stage:'step3_monitor'});
  expect(screen.getByText(/不重新准备/)).toBeInTheDocument();
});

it('reuses confirmation for an interrupted observer, not a running reconnect or compute wait', async () => {
  const detail = {pipeline:'gatk',execution_mode:'cce',recovery:{state:'needs_attention',stage_code:'step3_monitor',limit:6,generation:2}} as api.RunDetail;
  expect(monitorReconnectAvailable(detail,true)).toBe(true);
  expect(monitorReconnectAvailable(detail,false)).toBe(false);
  expect(monitorReconnectAvailable({...detail,recovery:{...detail.recovery!,state:'checking'}},true)).toBe(false);
  expect(monitorReconnectAvailable({...detail,recovery:{...detail.recovery!,limit:2}},true)).toBe(false);
  expect(monitorReconnectAvailable({...detail,execution_mode:'local'},true)).toBe(false);
  const submit=vi.spyOn(api,'resumeStage').mockResolvedValue({analysis_id:'mock',attempt:1,stage:'step3_monitor',generation:3,action_id:'manual',status:'queued'});
  render(<ResumeStagePanel analysisId="mock" attempt={1} stage="step3_monitor" reconnect canOperate onAccepted={() => undefined}/>);
  const button=screen.getByRole('button',{name:'恢复监控'});
  expect(button).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(button);
  await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
  expect(submit.mock.calls[0][1]).toMatchObject({attempt:1,stage:'step3_monitor'});
});
