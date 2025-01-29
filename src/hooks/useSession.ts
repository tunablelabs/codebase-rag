import { useState, useCallback } from 'react';

import { QueryMetrics } from "@/types/index";
interface Session {
  id: string;
  name: string;
  messages: Array<{
    type: 'user' | 'bot';
    text: string;
    timestamp: string;
    metric?: QueryMetrics;
  }>;
  createdAt: string;
  lastActive: string;
}

export function useSession() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const currentSession = sessions.find(s => s.id === currentSessionId);

  const createSession = useCallback((name: string, id: string) => {
    const newSession: Session = {
      id: id,
      name,
      messages: [],
      createdAt: new Date().toISOString(),
      lastActive: new Date().toISOString(),
    };

    setSessions(prev => [...prev, newSession]);
    setCurrentSessionId(newSession.id);
    return newSession;
  }, []);

  const updateSession = useCallback((
    sessionId: string,
    updates: Partial<Omit<Session, 'id'>>
  ) => {
    setSessions(prev => prev.map(session => 
      session.id === sessionId
        ? { ...session, ...updates, lastActive: new Date().toISOString() }
        : session
    ));
  }, []);

  const deleteSession = useCallback((sessionId: string) => {
    setSessions(prev => prev.filter(session => session.id !== sessionId));
    if (currentSessionId === sessionId) {
      setCurrentSessionId(null);
    }
  }, [currentSessionId]);

  const addMessageToSession = useCallback((
    sessionId: string,
    message: { type: 'user' | 'bot'; text: string; metric?: Metric}
  ) => {
    setSessions(prev => prev.map(session => {
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
      return session;
    }));
  }, []);

  return {
    sessions,
    currentSession,
    currentSessionId,
    isLoading,
    createSession,
    updateSession,
    deleteSession,
    setCurrentSessionId,
    addMessageToSession,
    setSessions
  };
}
