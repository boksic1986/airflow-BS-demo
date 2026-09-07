import {createContext, useContext, useEffect, useMemo, useState, type ReactNode} from "react";

import {getPlatformCapabilities, type DeployedPipeline, type PlatformCapabilities} from "../../api";
import {errorMessage} from "../../lib/errors";

function normalizeCapabilities(payload: PlatformCapabilities): PlatformCapabilities {
  const deployed = Array.isArray(payload.deployed_pipelines) && payload.deployed_pipelines.length
    ? payload.deployed_pipelines
    : [];
  const pipelines = Array.isArray(payload.pipelines) && payload.pipelines.length
    ? payload.pipelines
    : deployed.map((id) => ({
      id,
      display_name: id.split(/[._-]+/).map((part) => part.toUpperCase()).join(" "),
      dag_id: "",
      version: null,
      enabled: true,
      submit_enabled: true,
      capabilities: [],
      execution_targets: [],
    }));
  return {...fallbackCapabilities, ...payload, deployed_pipelines: deployed, pipelines};
}

const fallbackCapabilities: PlatformCapabilities = {
  environment: "NGS platform",
  deployed_pipelines: [],
  pipelines: [],
  airflow_url: null,
};

type PlatformContextValue = PlatformCapabilities & {
  loading: boolean;
  error: string | null;
  isDeployed: (pipeline: DeployedPipeline) => boolean;
};

const PlatformContext = createContext<PlatformContextValue>({
  ...fallbackCapabilities,
  loading: true,
  error: null,
  isDeployed: (pipeline) => fallbackCapabilities.deployed_pipelines.includes(pipeline),
});

export function PlatformCapabilitiesProvider({children}: {children: ReactNode}) {
  const [capabilities, setCapabilities] = useState<PlatformCapabilities>(fallbackCapabilities);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    getPlatformCapabilities()
      .then((payload) => {
        if (!disposed) {
          setCapabilities(normalizeCapabilities(payload));
          setError(null);
        }
      })
      .catch((loadError) => {
        if (!disposed) setError(errorMessage(loadError));
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });
    return () => { disposed = true; };
  }, []);

  const value = useMemo<PlatformContextValue>(() => ({
    ...capabilities,
    loading,
    error,
    isDeployed: (pipeline) => capabilities.deployed_pipelines.includes(pipeline),
  }), [capabilities, error, loading]);

  return <PlatformContext.Provider value={value}>{children}</PlatformContext.Provider>;
}

export function usePlatformCapabilities(): PlatformContextValue {
  return useContext(PlatformContext);
}
