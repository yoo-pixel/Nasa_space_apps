import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type CrewSelection = { activeAstronautId: string; setActiveAstronautId: (id: string) => void };
const CrewSelectionContext = createContext<CrewSelection | null>(null);
const storageKey = "astroguard.active-astronaut-id";

function readStoredAstronaut() {
  try { return window.localStorage.getItem(storageKey) || ""; }
  catch { return ""; }
}

export function CrewSelectionProvider({ children }: { children: ReactNode }) {
  const [activeAstronautId, setActive] = useState(readStoredAstronaut);
  const setActiveAstronautId = useCallback((id: string) => {
    setActive(id);
    try { window.localStorage.setItem(storageKey, id); }
    catch { /* Keep the in-memory selection when browser storage is unavailable. */ }
  }, []);
  return <CrewSelectionContext.Provider value={{ activeAstronautId, setActiveAstronautId }}>{children}</CrewSelectionContext.Provider>;
}

export function useCrewSelection() {
  const value = useContext(CrewSelectionContext);
  if (!value) throw new Error("useCrewSelection must be used inside CrewSelectionProvider");
  return value;
}
