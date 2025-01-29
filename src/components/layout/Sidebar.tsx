import { Session } from "@/types";
import { useState, useEffect } from "react";
import { FolderUp, Plus, X } from 'lucide-react';
//import { useSession } from "@/hooks/useSession";
import { useSessionContext } from "@/context/SessionProvider";
import { useFileUpload } from "@/hooks/useFileUpload"
import { useGithubUrl } from "@/hooks/useGithubUrl"

interface Stats {
  total_code_files: number;
  language_distribution: {
    [language: string]: string; 
  };
}

interface SidebarProps {
  onFileUpload: (files: FileList) => void;
  handlestatsUpload: (stats: Stats) =>void;
}

declare module 'react' {
  interface InputHTMLAttributes<T> extends HTMLAttributes<T> {
    webkitdirectory?: string;
  }
}

export default function Sidebar({
  onFileUpload,
  handlestatsUpload
}: SidebarProps) {
  const { sessions, currentSessionId, createSession, setCurrentSessionId } = useSessionContext();
  const { uploadFiles, sessionIdf } = useFileUpload()
  const { uploadUrl, sessionId } = useGithubUrl()
  const [isInputVisible, setInputVisible] = useState(false);
  const [newSessionName, setNewSessionName] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  
  useEffect(() => {
    if (sessionId) {
      console.log("Session ID updated:", sessionId);
      createSession(newSessionName,sessionId);
      setNewSessionName("");
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionIdf) {
      console.log("Session ID updated:", sessionIdf);
      createSession(newSessionName,sessionIdf);
      setNewSessionName("");
    }
  }, [sessionIdf]);

 

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;
    if (!selectedFiles) return;
    setSelectedFiles(selectedFiles);
    const folderPath = selectedFiles[0].webkitRelativePath.split("/")[0];
    setNewSessionName(folderPath);
    onFileUpload(selectedFiles);
  };

  const handleUrlChange = async (url : string) => {
    setNewSessionName(url);
    setGithubUrl(url);
    //uploadUrl(url);
  };

  const extractRepoName = (githubUrl: string) => {
    const regex = /github\.com\/([^\/]+)\/([^\/]+)(\.git)?/;
    const match = githubUrl.match(regex);
    return match ? match[2] : '';
  };

  const handleCreateSession = async () => {
    if (newSessionName) {

      setIsUploading(true);
      
      try
      {
        if (githubUrl) {
          let newses= extractRepoName(githubUrl)
          setNewSessionName(newses)
          let stats = await uploadUrl(githubUrl); // Upload GitHub repo only when button is clicked
          handlestatsUpload(stats.stats);
          
        } else if (selectedFiles) {
          let stats = await uploadFiles(selectedFiles); 
          console.log('session_fromfiles',stats.stats);
          handlestatsUpload(stats.stats);
          //createSession(newSessionName,ses_name);
          //setNewSessionName("");
       
        }
      
        setGithubUrl("");
        setSelectedFiles(null);
        setInputVisible(false);
        setIsUploading(false);
      }
      catch (err) {
        alert("I can only parse python, Java and Javascript files");
        throw err;
      }
      finally {
        setGithubUrl("");
        setSelectedFiles(null);
        setInputVisible(false);
        setIsUploading(false);
      }
      
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
                onChange={(e) => {
                  const value = e.target.value;
                  setNewSessionName(value);  // Update the state with the input value
                  handleUrlChange(value); 
                }}
                className="input input-bordered w-full"
                placeholder="Enter the Github Repository URL"
                disabled={isUploading}
              />

              <div className="flex flex-col sm:flex-row gap-4">
                <label className="flex-1">
                  <input
                    type="file"
                    webkitdirectory="true"
                    onChange={handleFileChange}
                    className="hidden"
                    disabled={isUploading}
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
                    disabled={isUploading}
                  >
                      {isUploading ? (
                        <>
                          <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                            <circle
                              className="opacity-25"
                              cx="12"
                              cy="12"
                              r="10"
                              stroke="currentColor"
                              strokeWidth="4"
                              fill="none"
                            />
                            <path
                              className="opacity-75"
                              fill="currentColor"
                              d="M4 12a8 8 0 018-8v4l4-4-4-4v4a8 8 0 00-8 8z"
                            />
                          </svg>
                          Uploading...
                        </>
                      ) : (
                        "Create Session"
                      )}
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
            onClick={() => setCurrentSessionId(session.id)}
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