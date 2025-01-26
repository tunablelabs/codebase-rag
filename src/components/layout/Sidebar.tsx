import { Session } from "@/types";
import { useState } from "react";
import { FolderUp, Plus, X } from 'lucide-react';

interface SidebarProps {
  sessions: Session[];
  currentSessionId: string | null;
  onCreateSession: (name: string, githubUrl: string) => Promise<Session>;
  onSessionSelect: (id: string) => void;
  onFileUpload: (files: FileList) => void;
  setGithubUrl: (url: string) => void;
}

declare module 'react' {
  interface InputHTMLAttributes<T> extends HTMLAttributes<T> {
    webkitdirectory?: string;
  }
}

export default function Sidebar({
  sessions,
  currentSessionId,
  onCreateSession,
  onSessionSelect,
  onFileUpload,
  setGithubUrl,
}: SidebarProps) {
  const [isInputVisible, setInputVisible] = useState(false);
  const [newSessionName, setNewSessionName] = useState("");

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;
    if (!selectedFiles) return;

    const folderPath = selectedFiles[0].webkitRelativePath.split("/")[0];
    setNewSessionName(folderPath);
    setGithubUrl(folderPath);
    onFileUpload(selectedFiles);
  };

  const handleCreateSession = async () => {
    if (newSessionName) {
      await onCreateSession(newSessionName, newSessionName);
      setNewSessionName("");
      setInputVisible(false);
    }
  };

  return (
    <div className="w-64 p-6 space-y-4 flex flex-col bg-base-100 border-r border-base-300 dark:border-base-700">
      <button 
        onClick={() => setInputVisible(true)} 
        className="btn btn-primary gap-2 h-auto py-3 px-4 font-semibold normal-case"
      >
        <Plus className="w-5 h-5" />
        New Chat
      </button>

      {isInputVisible && (
        <div className="fixed inset-0 bg-base-300/50 backdrop-blur-sm flex justify-center items-center z-50">
          <div className="bg-base-100 rounded-xl shadow-xl p-6 w-[500px] max-w-[90vw] border border-base-300 dark:border-base-700">
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-base-content">Create New Session</h3>
                <button 
                  onClick={() => setInputVisible(false)}
                  className="btn btn-ghost btn-sm btn-circle"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <input
                type="text"
                value={newSessionName}
                onChange={(e) => setNewSessionName(e.target.value)}
                className="input input-bordered w-full"
                placeholder="Enter the Github Repository URL"
              />

              <div className="flex flex-col sm:flex-row gap-4">
                <label className="flex-1">
                  <input
                    type="file"
                    webkitdirectory="true"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <div className="btn btn-secondary w-full flex items-center justify-center gap-2">
                    <FolderUp className="w-5 h-5" />
                    Upload Folder
                  </div>
                </label>

                <div className="flex gap-2 flex-1">
                  <button
                    onClick={handleCreateSession}
                    className="btn btn-primary flex-1"
                  >
                    Create Session
                  </button>

                  <button
                    onClick={() => setInputVisible(false)}
                    className="btn btn-ghost"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 space-y-1.5">
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onSessionSelect(session.id)}
            className={`w-full px-4 py-3 rounded-lg transition-all text-left group
              ${currentSessionId === session.id
                ? 'bg-primary/10 text-primary hover:bg-primary/20'
                : 'hover:bg-base-200 text-base-content/80 hover:text-base-content'
              }
            `}
          >
            <div className="flex items-center gap-2">
              <span className="flex-1 truncate">{session.name}</span>
              {currentSessionId === session.id && (
                <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}