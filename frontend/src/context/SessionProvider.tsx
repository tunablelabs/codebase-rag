"use client";
import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { api } from '@/services/api';
import { QueryMetrics } from "@/types/index";
import { createClient } from "@/utils/supabase/client";
import { Session } from '@/types';
import { format } from 'path';

interface SessionContextType {
  sessions: Session[];
  currentSession?: Session;
  currentSessionId: string | null;
  email: string; 
  isLoading: boolean;
  createSession: (name: string, id: string) => Session;
  addMessageToSession: (sessionId: string, message: { type: 'user' | 'bot'; text: string; metric?: QueryMetrics; id?: string }) => void;
  updateSessionMessage: (sessionId: string, messageId: string, updatedMessage: { type: 'user' | 'bot'; text: string; metric?: QueryMetrics }) => void;
  setSessions: React.Dispatch<React.SetStateAction<Session[]>>;
  setCurrentSessionId: React.Dispatch<React.SetStateAction<string | null>>;
  renameSession: (sessionId: string, newName: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
}

export const SessionContext = createContext<SessionContextType | null>(null); // Export SessionContext

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const hasFetchedRef = useRef(false);
  const [email, setEmail] = useState<string | null>(null);
  const currentSession = sessions.find(s => s.session_id === currentSessionId);

  useEffect(() => {
    const fetchUser = async () => {
      const supabase = await createClient();
      const { data } = await supabase.auth.getUser();
      if (data?.user?.email) {
        console.log('from sessionprovider',data.user.email)
        setEmail(data.user.email ?? "");
      }
    };

    fetchUser();
  }, []);

  const fetchSessions = async () => {
    if (!email) return;
    try {
      setIsLoading(true);
      console.log("[SessionProvider] Fetching sessions...");
      const chatSessions = await api.listAllSessions(email);
      console.log(chatSessions)
      const formattedSessions = chatSessions.map(chat => ({
        session_id: chat.session_id,
        project_name: chat.project_name || 'New Chat',
        messages: chat.messages.flatMap(msg => {
          const messages = [];
          if (msg.query) {
            messages.push({
              id: Date.now().toString() + Math.random().toString(36).substring(2, 9),
              type: 'user' as const,
              text: msg.query,
              timestamp: new Date().toISOString()
            });
          }
          if (msg.response) {
            messages.push({
              id: Date.now().toString() + Math.random().toString(36).substring(2, 9),
              type: 'bot' as const,
              text: msg.response,
              timestamp: new Date().toISOString(),
              metric: msg.metrics
            });
          }
          return messages;
        }),
        createdAt: new Date().toISOString(),
        lastActive: new Date().toISOString() 
      }));
      console.log(formattedSessions)
      setSessions(formattedSessions);
    } catch (error) {
      console.error('[SessionProvider] Error fetching sessions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!hasFetchedRef.current && email) {
      hasFetchedRef.current = true;
      fetchSessions();
    }
  }, [email]);

  const createSession = (name: string, id: string) => {
    console.log('recieved at back')
    const newSession: Session = {
      session_id: id,
      project_name: name,
      messages: [],
      createdAt: new Date().toISOString(),
      lastActive: new Date().toISOString(),
    };
    setSessions(prev => [...prev, newSession]);
    setCurrentSessionId(newSession.session_id);
    return newSession;
  };

  const addMessageToSession = (
    sessionId: string,
    message: { type: 'user' | 'bot'; text: string; metric?: QueryMetrics; id?: string }
  ) => {
    console.log('added to session',sessionId, message)
    setSessions(prev => prev.map(session => {
      console.log("inside",session)
      if (session.session_id === sessionId) {
        return {
          ...session,
          messages: [...session.messages, {
            ...message,
            id: message.id || Date.now().toString() + Math.random().toString(36).substring(2, 9),
            timestamp: new Date().toISOString(),
          }],
          lastActive: new Date().toISOString(),
        };
      }
      console.log('current_session',sessions)
      return session;
    }));
  };

  // New function to update an existing message in a session
  const updateSessionMessage = (
    sessionId: string,
    messageId: string,
    updatedMessage: { type: 'user' | 'bot'; text: string; metric?: QueryMetrics }
  ) => {
    setSessions(prev => prev.map(session => {
      if (session.session_id === sessionId) {
        return {
          ...session,
          messages: session.messages.map(message => {
            if (message.id === messageId) {
              return {
                ...message,
                ...updatedMessage,
                id: messageId,
                timestamp: message.timestamp, // Keep original timestamp
              };
            }
            return message;
          }),
          lastActive: new Date().toISOString(),
        };
      }
      return session;
    }));

  // new function to rename a session
  const renameSession = async (sessionId: string, newName: string): Promise<void> => {
    if (!email) return;
    
    try {
      setIsLoading(true);
      
      // calling the API to update the session name on the server
      await api.renameSession({
        session_id: sessionId,
        new_name: newName,
        email: email
      });
      
      setSessions(prev => prev.map(session => {
        if (session.session_id === sessionId) {
          return {
            ...session,
            project_name: newName,
            lastActive: new Date().toISOString()
          };
        }
        return session;
      }));
      
      console.log(`Session ${sessionId} renamed to "${newName}"`);
    } catch (error) {
      console.error('[SessionProvider] Error renaming session:', error);
      throw error; 
    } finally {
      setIsLoading(false);
    }
  };

  // new function to delete a session
  const deleteSession = async (sessionId: string): Promise<void> => {
    if (!email) return;
    
    try {
      setIsLoading(true);
      
      // calling the API to delete the session on the server
      await api.deleteSession({
        session_id: sessionId,
        email: email
      });
      
      setSessions(prev => prev.filter(session => session.session_id !== sessionId));
      
      if (currentSessionId === sessionId) {
        const remainingSessions = sessions.filter(s => s.session_id !== sessionId);
        if (remainingSessions.length > 0) {
          setCurrentSessionId(remainingSessions[0].session_id);
        } else {
          setCurrentSessionId(null);
        }
      }
      
      console.log(`Session ${sessionId} deleted successfully`);
    } catch (error) {
      console.error('[SessionProvider] Error deleting session:', error);
      throw error; 
    } finally {
      setIsLoading(false);
    }

  };

  return (
    <SessionContext.Provider value={{ 
      sessions, 
      setSessions, 
      email: email ?? "", 
      currentSessionId, 
      currentSession, 
      isLoading, 
      createSession, 
      addMessageToSession, 
      updateSessionMessage, 
      setCurrentSessionId,
      renameSession,
      deleteSession
    }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSessionContext() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSessionContext must be used within a SessionProvider");
  }
  return context;
}