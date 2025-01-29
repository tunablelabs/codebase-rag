import React, { useState } from 'react';
import { FolderUp, X } from 'lucide-react';

interface NewSessionButtonProps {
  onCreateSession: (name: string, githubUrl: string) => void;
  onFileUpload: (files: FileList) => void;
}

export default function NewSessionButton({ onCreateSession, onFileUpload }: NewSessionButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [sessionName, setSessionName] = useState('');
  const [githubUrl, setGithubUrl] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (sessionName.trim() || githubUrl.trim()) {
      onCreateSession(sessionName, githubUrl);
      setSessionName('');
      setGithubUrl('');
      setIsModalOpen(false);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      const folderName = files[0].webkitRelativePath.split('/')[0];
      setSessionName(folderName);
      onFileUpload(files);
      setIsModalOpen(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setIsModalOpen(true)}
        className="w-full px-4 py-3 bg-gradient-to-r from-blue-500 to-blue-600 
          hover:from-blue-600 hover:to-blue-700
          text-white rounded-lg transition-all duration-200 
          shadow-md hover:shadow-lg
          flex items-center justify-center gap-2 font-medium"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          strokeWidth="2"
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

      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex justify-center items-center z-50">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-lg transform transition-all">
            <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                Create New Session
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-500 dark:hover:text-slate-300
                  transition-colors rounded-lg p-1
                  hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                    GitHub Repository URL
                  </label>
                  <input
                    type="text"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-lg border border-slate-200 
                      dark:border-slate-600 dark:bg-slate-700
                      focus:ring-2 focus:ring-blue-500 focus:border-transparent
                      transition-colors dark:text-white
                      placeholder:text-slate-400 dark:placeholder:text-slate-500"
                    placeholder="https://github.com/username/repo"
                  />
                </div>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-slate-200 dark:border-slate-700"></div>
                  </div>
                  <div className="relative flex justify-center">
                    <span className="bg-white dark:bg-slate-800 px-2 text-sm text-slate-500">
                      or
                    </span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                    Upload Local Repository
                  </label>
                  <div className="mt-1">
                    <input
                      type="file"
                      webkitdirectory="true"
                      onChange={handleFileChange}
                      className="hidden"
                      id="folder-upload"
                    />
                    <label
                      htmlFor="folder-upload"
                      className="flex items-center justify-center px-4 py-2.5
                        border-2 border-dashed border-slate-300 dark:border-slate-600
                        rounded-lg cursor-pointer
                        hover:border-blue-500 dark:hover:border-blue-400
                        transition-colors group"
                    >
                      <FolderUp className="w-5 h-5 mr-2 text-slate-400 
                        group-hover:text-blue-500 dark:group-hover:text-blue-400
                        transition-colors" />
                      <span className="text-sm font-medium text-slate-600 
                        dark:text-slate-400 group-hover:text-blue-500 
                        dark:group-hover:text-blue-400 transition-colors">
                        Choose Folder
                      </span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-700 
                    dark:text-slate-300 hover:bg-slate-100 
                    dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600
                    text-white text-sm font-medium rounded-lg
                    transition-colors shadow-sm"
                >
                  Create Session
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}