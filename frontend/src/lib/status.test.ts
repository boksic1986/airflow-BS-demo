import {describe, expect, it} from "vitest";

import {getStatusMeta, isActiveStatus, statusPriority} from "./status";

describe("WGS transfer lifecycle statuses", () => {
  it.each([
    ["publishing", "publishing"],
    ["downloading", "downloading"],
  ])("treats %s as an active operator-visible status", (status, label) => {
    expect(isActiveStatus(status)).toBe(true);
    expect(getStatusMeta(status)).toMatchObject({label, active: true, terminal: false});
    expect(statusPriority(status)).toBe(1);
  });
});
