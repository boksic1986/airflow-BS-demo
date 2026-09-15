import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import {afterEach, expect, it, vi} from 'vitest';
import {ResumeStagePanel} from './ResumeStagePanel';
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
