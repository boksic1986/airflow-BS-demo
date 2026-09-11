import '@testing-library/jest-dom/vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {afterEach, beforeEach, expect, it} from 'vitest';
import {OperationsOverview} from './DashboardOverview';
import type {DashboardOverview} from '../../api';

beforeEach(() => localStorage.clear());
afterEach(cleanup);
const warning = {id:'review-a1',category:'duplicate_family',severity:'warning',title:'Review family',detail:'Batch A and B',analysis_id:null};
function show(items: unknown[]) {return render(<MemoryRouter><OperationsOverview overview={{attention_items:items} as DashboardOverview} period="7d" loading={false} onPeriodChange={()=>{}} /></MemoryRouter>);}
it('keeps informational history collapsed and lets the user open it',()=>{
 show([{...warning,id:'info-a1',category:'reanalysis',severity:'info',title:'Reanalysis recorded'}]);
 expect(screen.queryByText('Reanalysis recorded')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:/历史与已确认/}));
 expect(screen.getByText('Reanalysis recorded')).toBeInTheDocument();
});
it('retains an acknowledgement across remount but resurfaces a new condition',()=>{
 const first=show([warning]);fireEvent.click(screen.getByRole('button',{name:'确认提醒'}));
 first.unmount();const second=show([warning]);expect(screen.queryByText('Review family')).not.toBeInTheDocument();
 second.unmount();show([{...warning,id:'review-a2'}]);expect(screen.getByText('Review family')).toBeInTheDocument();
});
