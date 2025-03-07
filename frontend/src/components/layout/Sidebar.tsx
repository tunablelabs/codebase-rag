import { useState, useEffect } from "react";
import { Edit2, FolderUp, Plus, Trash2, X, Search, Calendar, Check } from 'lucide-react';
import { useSessionContext } from "@/context/SessionProvider";
import { useFileUpload } from "@/hooks/useFileUpload"
import { useGithubUrl } from "@/hooks/useGithubUrl"
import UploadProgress from "@/components/layout/UploadProgress"; // Import the new component

interface Stats {
  total_code_files: number;
  language_distribution: {
    [language: string]: string; 
  };
}

interface APIResponse {
  stats: Stats;
}

interface SidebarProps {
  onFileUpload: (files: FileList) => void;
  handlestatsUpload: (stats: Stats) => void;
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
  const { sessions, email, currentSessionId, createSession, setCurrentSessionId, renameSession, deleteSession} = useSessionContext();
  const { uploadFiles, sessionIdf } = useFileUpload()
  const { uploadUrl, sessionId } = useGithubUrl()
  const [isInputVisible, setInputVisible] = useState(false);
  const [newSessionName, setNewSessionName] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [renameSessionId, setRenameSessionId] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  const filteredSessions = sessions?.filter(session => 
    session.project_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  useEffect(() => {
    if (sessionId) {
      createSession(newSessionName,sessionId);
      setNewSessionName("");
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionIdf) {
      createSession(newSessionName,sessionIdf);
      setNewSessionName("");
    }
  }, [sessionIdf]);

  const displaySuccess = (message: string) => {
    setSuccessMessage(message);
    setShowSuccess(true);
    setTimeout(() => {
      setShowSuccess(false);
    }, 3000);
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;
    if (!selectedFiles) return;
    setSelectedFiles(selectedFiles);
    const folderPath = selectedFiles[0].webkitRelativePath.split("/")[0];
    setNewSessionName(folderPath);
    onFileUpload(selectedFiles);
  };

  const handleUrlChange = async (url: string) => {
    setNewSessionName(url);
    setGithubUrl(url);
  };

  const extractRepoName = (githubUrl: string) => {
    const regex = /github\.com\/([^\/]+)\/([^\/]+)(\.git)?/;
    const match = githubUrl.match(regex);
    return match ? match[2] : '';
  };

  const handleCreateSession = async () => {
    if (newSessionName) {
      setIsUploading(true);
      setUploadError(null);
      
      try {
        if (githubUrl) {
          const newses = extractRepoName(githubUrl)
          setNewSessionName(newses)
          const rawResponse = await uploadUrl(githubUrl,email);
          const response = rawResponse as unknown as APIResponse;
          if (response?.stats) {
            handlestatsUpload(response.stats);
            displaySuccess("Repository successfully imported!");
          }
        } else if (selectedFiles) {
          const rawResponse = await uploadFiles(selectedFiles,email);
          const response = rawResponse as unknown as APIResponse;
          console.log('session_fromfiles', response?.stats);
          if (response?.stats) {
            handlestatsUpload(response.stats);
            displaySuccess("Files successfully uploaded!");
          }
        }
      }
      catch (err) {
        setUploadError("An unexpected error occurred. Please try again.");
        console.error("Upload error:", err);
      }
    }
  };

  const handleUploadComplete = () => {
    setGithubUrl("");
    setSelectedFiles(null);
    setInputVisible(false);
    setIsUploading(false);
  };

  const handleStartRename = (sessionId: string, currentName: string, e: React.MouseEvent) => {
    e.stopPropagation(); 
    setRenameSessionId(sessionId);
    setNewName(currentName);
  };
  
  const handleRenameSubmit = async (sessionId: string) => {
    if (newName.trim()) {
      try {
        await renameSession(sessionId, newName.trim());
        setRenameSessionId(null);
        setNewName("");
        displaySuccess("Chat renamed successfully!");
      } catch (error) {
        console.error("Error renaming chat:", error);
        alert("Failed to rename chat. Please try again.");
      }
    }
  };
  
  const handleRenameCancel = () => {
    setRenameSessionId(null);
    setNewName("");
  };
  
  // new handler for delete functionality
  const handleDelete = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation(); 
    if (window.confirm("Are you sure you want to delete this chat?")) {
      try {
        await deleteSession(sessionId);
        displaySuccess("Chat deleted successfully!");
        
        if (currentSessionId === sessionId && sessions.length > 1) {
          const newCurrentSession = sessions.find(s => s.session_id !== sessionId);
          if (newCurrentSession) {
            setCurrentSessionId(newCurrentSession.session_id);
          }
        }
      } catch (error) {
        console.error("Error deleting chat:", error);
        alert("Failed to delete chat. Please try again.");
      }
    }
  };

  const handleRenameKeyPress = (e: React.KeyboardEvent, sessionId: string) => {
    if (e.key === 'Enter') {
      handleRenameSubmit(sessionId);
    } else if (e.key === 'Escape') {
      handleRenameCancel();
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="w-72 flex flex-col h-full bg-base-100 border-r border-base-300 dark:border-base-700 shadow-sm">
      {/* Success notification */}
      {showSuccess && (
        <div className="fixed top-4 right-4 bg-green-100 border-l-4 border-green-500 text-green-700 p-4 rounded shadow-md z-50 animate-fadeIn">
          <div className="flex items-center">
            <Check className="w-5 h-5 mr-2" />
            <p>{successMessage}</p>
          </div>
        </div>
      )}
      
      {/* Header section */}
      <div className="p-4 border-b border-base-300 dark:border-base-700">
        <button 
          onClick={() => setInputVisible(true)} 
          className="btn btn-primary w-full gap-2 py-3 px-4 font-semibold normal-case shadow-sm hover:shadow-md transition-all duration-300"
        >
          <Plus className="w-5 h-5" />
          New Chat
        </button>
      </div>

      {/* Search input */}
      <div className="px-4 py-3 border-b border-base-300 dark:border-base-700">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-base-content/60" />
          </div>
          <input
            type="text"
            className="input input-sm input-bordered w-full pl-10"
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute inset-y-0 right-0 pr-3 flex items-center"
            >
              <X className="h-4 w-4 text-base-content/60 hover:text-base-content" />
            </button>
          )}
        </div>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto p-2">
        {filteredSessions && filteredSessions.length > 0 ? (
          <div className="space-y-1">
            {filteredSessions.map((session) => (
              <div key={session.session_id} className="group relative transition-all duration-200">
                {renameSessionId === session.session_id ? (
                  // Rename input field
                  <div className="flex items-center p-2 rounded-lg bg-base-200 shadow-inner">
                    <input
                      type="text"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      onKeyDown={(e) => handleRenameKeyPress(e, session.session_id)}
                      className="input input-sm input-bordered flex-1 mr-1 transition-all duration-200 focus:ring-2 focus:ring-primary/30"
                      autoFocus
                    />
                    <button
                      onClick={() => handleRenameSubmit(session.session_id)}
                      className="btn btn-sm btn-primary btn-circle"
                      title="Save"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={handleRenameCancel}
                      className="btn btn-sm btn-ghost btn-circle ml-1"
                      title="Cancel"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  // Normal session button with hover actions
                  <div 
                    className={`relative rounded-lg transition-all duration-200 
                      ${currentSessionId === session.session_id 
                        ? 'bg-primary/10 ring-1 ring-primary/40 shadow-sm' 
                        : 'hover:bg-base-200 group-hover:shadow-sm'
                      }`}
                  >
                    <button
                      onClick={() => setCurrentSessionId(session.session_id)}
                      className={`w-full p-3 text-left transition-all duration-200
                        ${currentSessionId === session.session_id
                          ? 'text-primary font-medium' 
                          : 'text-base-content/80 hover:text-base-content'
                        }
                      `}
                    >
                      <div className="flex flex-col space-y-1">
                        <div className="flex items-start justify-between">
                          <span className="truncate pr-6 text-sm font-medium">
                            {session.project_name || 'New Chat'}
                          </span>
                          {session.lastActive && (
                            <span className="text-xs text-base-content/60 flex items-center ml-2 whitespace-nowrap">
                              <Calendar className="h-3 w-3 mr-1 inline" />
                              {formatDate(session.lastActive)}
                            </span>
                          )}
                        </div>
                        
                        {/* Preview of last message if available */}
                        {session.messages && session.messages.length > 0 && (
                          <p className="text-xs text-base-content/60 truncate">
                            {session.messages[session.messages.length - 1].text.substring(0, 40)}
                            {session.messages[session.messages.length - 1].text.length > 40 ? '...' : ''}
                          </p>
                        )}
                      </div>
                    </button>
                    
                    {/* Action buttons that appear on hover with improved styling */}
                    <div 
                      className={`absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center 
                        space-x-1 bg-base-100/90 dark:bg-base-900/90 p-1 rounded-md shadow-sm
                        ${currentSessionId === session.session_id 
                          ? 'opacity-100' 
                          : 'opacity-0 group-hover:opacity-100'
                        } transition-all duration-200`}
                    >
                      <button
                        onClick={(e) => handleStartRename(session.session_id, session.project_name || 'New Chat', e)}
                        className="btn btn-ghost btn-xs btn-circle bg-base-200/80 hover:bg-base-300/80"
                        title="Rename"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => handleDelete(session.session_id, e)}
                        className="btn btn-ghost btn-xs btn-circle bg-base-200/80 hover:bg-error/20 text-error/80 hover:text-error"
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center text-base-content/60 p-6">
            {searchQuery ? (
              <>
                <Search className="w-12 h-12 mb-2 text-base-content/30" />
                <p>No chats match your search</p>
                <button 
                  onClick={() => setSearchQuery("")}
                  className="mt-2 text-sm text-primary hover:underline"
                >
                  Clear search
                </button>
              </>
            ) : (
              <>
                <div className="w-16 h-16 rounded-full bg-base-200 flex items-center justify-center mb-4">
                  <Plus className="w-8 h-8 text-base-content/40" />
                </div>
                <p className="text-lg font-medium mb-1">No chats yet</p>
                <p className="text-sm mb-4">Start by creating a new chat</p>
                <button 
                  onClick={() => setInputVisible(true)}
                  className="btn btn-sm btn-primary"
                >
                  Create a new chat
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Create new session modal */}
      {isInputVisible && (
        <div className="fixed inset-0 bg-base-300/50 backdrop-blur-sm flex justify-center items-center z-50 transition-all duration-300">
          <div className="bg-base-100 rounded-xl shadow-xl p-6 w-[500px] max-w-[90vw] border border-base-300 dark:border-base-700 animate-fadeInUp">
            <div className="space-y-6">
              <div className="flex justify-between items-center border-b border-base-200 pb-4">
                <h3 className="text-lg font-semibold text-base-content">Create New Chat</h3>
                <button 
                  onClick={() => setInputVisible(false)}
                  className="btn btn-ghost btn-sm btn-circle hover:bg-base-200"
                  disabled={isUploading}
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {isUploading ? (
                <div className="py-4">
                  <UploadProgress 
                    isActive={isUploading} 
                    onComplete={handleUploadComplete}
                    error={uploadError}
                  />
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-base-content/80 block ml-1">
                      Repository URL
                    </label>
                    <input
                      type="text"
                      value={newSessionName}
                      onChange={(e) => {
                        const value = e.target.value;
                        setNewSessionName(value);
                        handleUrlChange(value); 
                      }}
                      className="input input-bordered w-full focus:ring-2 focus:ring-primary/30 transition-all duration-200"
                      placeholder="Enter the Github Repository URL"
                    />
                  </div>

                  <div className="text-center my-2 relative">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-base-300"></div>
                    </div>
                    <div className="relative flex justify-center">
                      <span className="bg-base-100 px-2 text-xs text-base-content/60">OR</span>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-4">
                    <label className="flex-1">
                      <input
                        type="file"
                        webkitdirectory="true"
                        onChange={handleFileChange}
                        className="hidden"
                      />
                      <div className="btn btn-secondary w-full flex items-center justify-center gap-2 hover:shadow-md transition-all duration-200">
                        <FolderUp className="w-5 h-5" />
                        Upload Folder
                      </div>
                    </label>

                    <div className="flex gap-2 flex-1">
                      <button
                        onClick={handleCreateSession}
                        className="btn btn-primary flex-1 hover:shadow-md transition-all duration-200"
                      >
                        Create Chat
                      </button>

                      <button
                        onClick={() => setInputVisible(false)}
                        className="btn btn-ghost hover:bg-base-200"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}