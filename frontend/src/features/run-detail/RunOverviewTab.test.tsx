import "@testing-library/jest-dom/vitest";
import {render, screen} from "@testing-library/react";
import {it, expect} from "vitest";
import type {RunDetail} from "../../api";
import {RunOverviewTab} from "./RunResourceTabs";

it("keeps batch identity, counts and QC together without sample attributes or duplicate evidence", () => {
  const {container} = render(<RunOverviewTab detail={{analysis_id:"MOCK",pipeline:"wgs",status:"running",params:{batch_no:"MOCK-BATCH"},pipeline_release_id:"release-only-in-evidence"} as RunDetail} samples={[]} sampleCount={3} batchQcStatus="warn" manifestSummary={{sample_count:3,family_count:1,order_count:2,test_projects:["sample-only-project"],project_path:"evidence-only-path"}} />);
  expect([...container.querySelectorAll("dt")].map(item => item.textContent)).toEqual(["Batch","Pipeline","Status","Batch QC","Samples / families","Orders","Operator","Created","Submitted","Started","Finished","Attempt","DAG run"]);
  expect(screen.getByText("3 / 1")).toBeInTheDocument();
  expect(screen.getByText("warn")).toBeInTheDocument();
  expect(screen.queryByText(/Batch manifest summary|sample-only-project|evidence-only-path|release-only-in-evidence/)).toBeNull();
});
