import {describe, expect, it} from "vitest";

import dockerfile from "../Dockerfile?raw";
import bsNginx from "../nginx.bs-nipt.conf?raw";
import defaultNginx from "../nginx.conf?raw";

describe("frontend nginx image contract", () => {
  it("builds the BS API gateway config by default", () => {
    expect(dockerfile).toContain("ARG NGINX_CONF=nginx.bs-nipt.conf");
    expect(dockerfile).toContain("COPY ${NGINX_CONF} /etc/nginx/conf.d/default.conf");
  });

  it.each([
    ["BS gateway", bsNginx],
    ["generic gateway", defaultNginx],
  ])("routes /api to FastAPI before the SPA fallback in %s", (_name, config) => {
    const apiLocation = config.indexOf("location ^~ /api/");
    const spaLocation = config.indexOf("location / {");

    expect(apiLocation).toBeGreaterThanOrEqual(0);
    expect(config).toContain("proxy_pass http://biodemo_backend;");
    expect(spaLocation).toBeGreaterThan(apiLocation);
    expect(config.slice(apiLocation, spaLocation)).not.toContain("try_files");
    expect(config).toContain("try_files $uri $uri/ /index.html;");
  });

  it.each([
    ["BS gateway", bsNginx],
    ["generic gateway", defaultNginx],
  ])("does not let the exact /api path fall through to the SPA in %s", (_name, config) => {
    const exactApiLocation = config.indexOf("location = /api");
    const spaLocation = config.indexOf("location / {");

    expect(exactApiLocation).toBeGreaterThanOrEqual(0);
    expect(exactApiLocation).toBeLessThan(spaLocation);
    expect(config.slice(exactApiLocation, spaLocation)).toMatch(/(?:proxy_pass http:\/\/biodemo_backend|return 30[178] \/api\/)/);
  });

  it("keeps the operator workstation allowlist on both BS gateway ports", () => {
    expect(bsNginx.match(/allow 172\.20\.8\.0\/24;/g)).toHaveLength(2);
    expect(bsNginx.match(/deny all;/g)).toHaveLength(2);
  });
});
