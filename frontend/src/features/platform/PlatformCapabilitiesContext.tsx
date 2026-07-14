import {createContext, useContext, useEffect, useMemo, useState, type ReactNode} from "react";

import {getPlatformCapabilities, type DeployedPipeline, type PlatformCapabilities} from "../../api";

const fallbackCapabilities: PlatformCapabilities = {
  environment: "Demo",
  deployed_pipelines: ["pgta", "nipt_docker"],
  airflow_url: null,
};

type PlatformContextValue = PlatformCapabilities & {
  loading: boolean;
  isDeployed: (pipeline: DeployedPipeline) => boolean;
};

const PlatformContext = createContext<PlatformContextValue>({
  ...fallbackCapabilities,
  loading: true,
  isDeployed: () => true,
});

export function PlatformCapabilitiesProvider({children}: {children: ReactNode}) {
  const [capabilities, setCapabilities] = useState<PlatformCapabilities>(fallbackCapabilities);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let disposed = false;
    getPlatformCapabilities()
      .then((payload) => {
        if (!disposed && payload.deployed_pipelines.length) setCapabilities(payload);
      })
      .catch(() => {
        // Compatibility fallback for older backend deployments during rolling upgrades.
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });
    return () => { disposed = true; };
  }, []);

  const value = useMemo<PlatformContextValue>(() => ({
    ...capabilities,
    loading,
    isDeployed: (pipeline) => capabilities.deployed_pipelines.includes(pipeline),
  }), [capabilities, loading]);

  return <PlatformContext.Provider value={value}>{children}</PlatformContext.Provider>;
}

export function usePlatformCapabilities(): PlatformContextValue {
  return useContext(PlatformContext);
}
