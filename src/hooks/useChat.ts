import { useState, useCallback } from 'react';
import { Message, ChatOptions, QueryResponse } from '@/types';
import api from '@/services/api';

interface ChatHookReturn {
  messages: Message[];
  isPending: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<Message | undefined>;
  clearMessages: () => void;
}

export function useChat(options: ChatOptions): ChatHookReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (content: string): Promise<Message | undefined> => {
    if (!options.sessionId) {
      setError('No active session found');
      return;
    }

    setIsPending(true);
    setError(null);

    try {
      const queryResponse = await api.queryRepository({
        file_id: options.sessionId,
        use_llm: "False",
        ast_flag: "True",
        query: content,
        limit: 3
      });

      const timestamp = new Date().toISOString();
      
      const userMessage: Message = {
        type: 'user',
        text: content,
        timestamp
      };

      const botMessage: Message = {
        type: 'bot',
        text: queryResponse.response,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, userMessage, botMessage]);
      return botMessage;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);
      throw err;
    } finally {
      setIsPending(false);
    }
  }, [options.sessionId, options.astFlag]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isPending,
    error,
    sendMessage,
    clearMessages
  };
}