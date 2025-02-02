"use client";
import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { useSession } from '@/hooks/useSession';
import { Session } from '@/types';
import { api } from '@/services/api';

const SessionContext = createContext<ReturnType<typeof useSession> | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const sessionState = useSession();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const hasFetchedRef = useRef(false);

  const fetchSessions = async () => {
    try {
      setIsLoading(true);
      console.log("[SessionProvider] Fetching sessions...");
      const chatSessions = await api.listAllSessions();

      const formattedSessions = chatSessions.map(chat => ({
        
        id: chat.file_id,
        name: chat.repo_name || 'New Chat',
        messages: chat.messages.flatMap(msg => {
          const messages = [];
          if (msg.user) {
            messages.push({
              type: 'user' as const,
              text: msg.user,
              timestamp: new Date().toISOString()
            });
          }
          if (msg.bot) {
            messages.push({
              type: 'bot' as const,
              text: msg.bot,
              timestamp: new Date().toISOString()
            });
          }
          return messages;
        }),
        createdAt: new Date().toISOString(),
        lastActive: new Date().toISOString()
      }));

      console.log("Formatted sessions:", formattedSessions);
      setSessions(formattedSessions);
      sessionState.setSessions(formattedSessions);
    } catch (error) {
      console.error('[SessionProvider] Error fetching sessions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!hasFetchedRef.current) {
      hasFetchedRef.current = true;
      fetchSessions();
    }
  }, []); // Empty dependency array since we only want to fetch once on mount

  return (
    <SessionContext.Provider value={{ ...sessionState, sessions }}>
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
