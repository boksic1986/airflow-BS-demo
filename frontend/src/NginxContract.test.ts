import {describe, expect, it} from "vitest";

import dockerfile from "../Dockerfile?raw";
import bsNginx from "../nginx.bs-nipt.conf?raw";
import defaultNginx from "../nginx.conf?raw";
import wgsNginx from "../nginx.wgs.conf?raw";

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

  it("allows the production operator workstation subnet through the WGS gateway", () => {
    expect(wgsNginx).toContain("allow 10.10.30.0/24;");
    expect(wgsNginx).toContain("deny all;");
  });

  it("refreshes the WGS application shell while caching only fingerprinted assets", () => {
    expect(wgsNginx).toMatch(/location = \/index\.html[\s\S]*Cache-Control "no-store, no-cache, must-revalidate"/);
    expect(wgsNginx).toMatch(/location \^~ \/assets\/[\s\S]*Cache-Control "public, max-age=31536000, immutable"/);
    expect(wgsNginx).toMatch(/location \/ \{[\s\S]*Cache-Control "no-store, no-cache, must-revalidate"[\s\S]*try_files \$uri \$uri\/ \/index\.html/);
  });
});
