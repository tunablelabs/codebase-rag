import React from 'react';

interface Session {
  id: string;
  name: string;
  createdAt?: string;
  lastMessage?: string;
}

interface SessionListProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onCreateNewSession: () => void;
}

export default function SessionList({
  sessions,
  currentSessionId,
  onSessionSelect,
  onCreateNewSession,
}: SessionListProps) {
  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={onCreateNewSession}
        className="w-full px-4 py-3 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          strokeWidth="1.5"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 4.5v15m7.5-7.5h-15"
          />
        </svg>
        New Chat
      </button>

      <div className="space-y-2">
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onSessionSelect(session.id)}
            className={`
              w-full px-4 py-3 rounded-lg transition-all duration-200
              ${currentSessionId === session.id
                ? 'bg-blue-500 text-white shadow-md'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-slate-700 dark:text-gray-200 dark:hover:bg-slate-600'
              }
            `}
          >
            <div className="flex flex-col items-start">
              <span className="font-medium">{session.name}</span>
              {session.lastMessage && (
                <span className="text-sm truncate opacity-70">
                  {session.lastMessage}
                </span>
              )}
              {session.createdAt && (
                <span className="text-xs opacity-50">
                  {format(new Date(session.createdAt), 'MMM d, yyyy')}
                </span>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}