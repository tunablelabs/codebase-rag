import { useState, useCallback } from 'react';

interface Session {
  id: string;
  name: string;
  messages: Array<{
    type: 'user' | 'bot';
    text: string;
    timestamp: string;
  }>;
  createdAt: string;
  lastActive: string;
}

export function useSession() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const currentSession = sessions.find(s => s.id === currentSessionId);

  const createSession = useCallback((name: string) => {
    const newSession: Session = {
      id: Date.now().toString(),
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
    message: { type: 'user' | 'bot'; text: string; }
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
  };
}
