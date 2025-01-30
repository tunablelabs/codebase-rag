import React from 'react';
import { format } from 'date-fns';

interface Message {
  type: 'user' | 'bot';
  text: string;
  timestamp?: string;
}

interface MessageItemProps {
  message: Message;
}

export default function MessageItem({ message }: MessageItemProps) {
  const formattedTimestamp = message.timestamp 
    ? format(new Date(message.timestamp), 'HH:mm')
    : '';

  return (
    <div className={`flex items-end gap-2 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>

      {message.type === 'bot' && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.82 14.687l-2.317-2.318a2.5 2.5 0 013.536-3.536l1.318 1.318m4.5 4.5l2.317 2.318a2.5 2.5 0 11-3.536 3.536l-1.318-1.318" />
          </svg>
        </div>
      )}

      <div className={`max-w-[80%] group relative`}>
        <div className={`
          rounded-2xl px-4 py-2.5 shadow-sm
          ${message.type === 'user' 
            ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white ml-4' 
            : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 mr-4'
          }
        `}>
          <pre className={`
            whitespace-pre-wrap font-sans text-sm
            ${message.type === 'user' 
              ? 'text-white' 
              : 'text-slate-800 dark:text-slate-200'
            }
          `}>
            {message.text}
          </pre>
        </div>
        
        
        {message.timestamp && (
          <div className={`
            absolute bottom-0 
            ${message.type === 'user' ? 'right-full mr-2' : 'left-full ml-2'}
            opacity-0 group-hover:opacity-100 transition-opacity
            text-xs text-slate-500 dark:text-slate-400
          `}>
            {formattedTimestamp}
          </div>
        )}
      </div>

  
      {message.type === 'user' && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
      )}
    </div>
  );
}