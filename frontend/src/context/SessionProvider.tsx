"use client";
import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { api } from '@/services/api';
import { QueryMetrics } from "@/types/index";

import { Session } from '@/types';
interface SessionContextType {
  sessions: Session[];
  currentSession?: Session;
  currentSessionId: string | null;
  isLoading: boolean;
  createSession: (name: string, id: string) => Session;
  addMessageToSession: (sessionId: string, message: { type: 'user' | 'bot'; text: string; metric?: QueryMetrics }) => void;
  setSessions: React.Dispatch<React.SetStateAction<Session[]>>;
  setCurrentSessionId: React.Dispatch<React.SetStateAction<string | null>>;
}

export const SessionContext = createContext<SessionContextType | null>(null); // Export SessionContext

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const hasFetchedRef = useRef(false);
  const currentSession = sessions.find(s => s.id === currentSessionId);

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

      setSessions(formattedSessions);
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
  }, []);

  const createSession = (name: string, id: string) => {
    console.log('recieved at back')
    const newSession: Session = {
      id,
      name,
      messages: [],
      createdAt: new Date().toISOString(),
      lastActive: new Date().toISOString(),
    };
    setSessions(prev => [...prev, newSession]);
    setCurrentSessionId(newSession.id);
    return newSession;
  };

  const addMessageToSession = (
    sessionId: string,
    message: { type: 'user' | 'bot'; text: string; metric?: QueryMetrics}
  ) => {
    console.log('added to session',sessionId, message)
    setSessions(prev => prev.map(session => {
      console.log("inside",session)
      if (session.id === sessionId) {
        return {
          ...session,
          messages: [...session.messages, {
            ...message,
            timestamp: new Date().toISOString(),
          }],
          lastActive: new Date().toISOString(),
        };
      }
      console.log('current_session',sessions)
      return session;
    }));
  };

  return (
    <SessionContext.Provider value={{ sessions, setSessions, currentSessionId, currentSession, isLoading, createSession, addMessageToSession, setCurrentSessionId}}>
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
