"use client";
import { createContext, useContext } from 'react';
import { useSession } from '@/hooks/useSession';

const SessionContext = createContext<ReturnType<typeof useSession> | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const sessionState = useSession(); // Use the custom hook

  return (
    <SessionContext.Provider value={sessionState}>
      {children}
    </SessionContext.Provider>
  );
}

// Custom hook to use the session context
export function useSessionContext() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSessionContext must be used within a SessionProvider");
  }
  return context;
}
