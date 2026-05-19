import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { capabilitiesApi } from "../api/modules/capabilities";
import type { WebchatCapabilitiesResponse } from "../api/types/capabilities";

interface CapabilityContextType {
  data: WebchatCapabilitiesResponse | null;
  loading: boolean;
  reload: () => Promise<void>;
}

const CapabilityContext = createContext<CapabilityContextType | undefined>(
  undefined
);

export function CapabilityProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<WebchatCapabilitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const response = await capabilitiesApi.get();
      setData(response);
    } catch (error) {
      console.error("Failed to load webchat capabilities:", error);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return (
    <CapabilityContext.Provider value={{ data, loading, reload }}>
      {children}
    </CapabilityContext.Provider>
  );
}

export function useCapabilities() {
  const context = useContext(CapabilityContext);
  if (!context) {
    throw new Error("useCapabilities must be used within a CapabilityProvider");
  }
  return context;
}
