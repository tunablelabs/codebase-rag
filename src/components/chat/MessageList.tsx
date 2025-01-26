import React, { useEffect, useRef } from 'react';
import MessageItem from './MessageItem';

interface Message {
  type: 'user' | 'bot';
  text: string;
  timestamp?: string;
}

interface MessageListProps {
  messages: Message[];
  isPending: boolean;
}

export default function MessageList({ messages, isPending }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {messages.length === 0 && !isPending && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-r from-blue-500 to-blue-600 flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300">
                Welcome to Code RAG Assistant
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Ask me anything about your code repository!
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Messages list */}
      {messages.length > 0 && (
        <div className="flex-1 space-y-4 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-200 hover:scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-700 dark:hover:scrollbar-thumb-slate-600">
          {messages.map((message, index) => (
            <MessageItem key={index} message={message} />
          ))}
        </div>
      )}

      {isPending && (
        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 py-4">
          <div className="flex space-x-1">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-sm font-medium">Thinking...</span>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
}