import React, { useState } from "react";

interface ChatSidebarProps {
  sessions: { id: string; messages: { type: "user" | "bot"; text: string }[] }[];
  createNewSession: (sessionName: string) => void;
  setCurrentSessionId: (id: string) => void;
  currentSessionId: string | null;
  setGithubUrl: React.Dispatch<React.SetStateAction<string>>;
  setFiles: React.Dispatch<React.SetStateAction<any[]>>; // or specify a more precise type for files
  setFolderName: React.Dispatch<React.SetStateAction<string>>;
  setIsFilesVisible: React.Dispatch<React.SetStateAction<boolean>>;
  
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  sessions,
  createNewSession,
  setCurrentSessionId,
  currentSessionId,
  setFiles,
  setFolderName,
  setIsFilesVisible,
  setGithubUrl
  
}) => {
  const [isInputVisible, setInputVisible] = useState(false);
  const [newSessionName, setNewSessionName] = useState("");

  const handleNewSessionClick = () => {
    setInputVisible(true);
  };

  const handleCreateSession = () => {
    if (newSessionName) {
      createNewSession(newSessionName);
      setNewSessionName("");
      setInputVisible(false);
    }
  };

  
  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;

    if (selectedFiles) {
      const file_names= Array.from(selectedFiles).map(file => file.name).slice(0, 3);
      setFiles(file_names);
      const firstFile = selectedFiles[0];
      const folderPath = firstFile.webkitRelativePath.split("/")[0];
      setFolderName(folderPath);
      const formData = new FormData();
      Array.from(selectedFiles).forEach((file) => {
        formData.append("files", file);
      });
      setIsFilesVisible(true);
      formData.append("directoryName", folderPath);
      setGithubUrl(folderPath);
      setNewSessionName(folderPath);

      try {
        const response = await fetch("/api/upload", {
          method: "POST",
          body: formData,
        });
        const result = await response.json();
        console.log("Upload result:", result);
      } catch (error) {
        console.error("Error uploading files:", error);
      }
    }
  };

  return (
    <div className="w-1/6 p-6 space-y-4 flex flex-col">
      <button onClick={handleNewSessionClick} className="bg-green-500 text-white px-4 py-2 rounded">
        New Chat
      </button>

      {/* Popup overlay */}
      {isInputVisible && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
          <div className="bg-white p-6 rounded-md w-[50%] space-y-4">

            <div className="flex gap-2">
                <input
                type="text"
                value={newSessionName}
                onChange={(e) => setNewSessionName(e.target.value)}
                className="border p-2 w-full"
                placeholder="Enter the Github Repository URL"
                />
                <label className="inline-flex cursor-pointer items-center rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700">
                    Upload Folder
                    <input
                    type="file"
                    id="file-upload"
                    webkitdirectory="true"
                    className="hidden"
                    onChange={handleFileChange}
                    />
                </label>
            </div>
            <div className="flex justify-between space-x-4">
              <button
                onClick={handleCreateSession}
                className="bg-blue-500 text-white px-4 py-2 rounded"
              >
                Create Session
              </button>
              <button
                onClick={() => setInputVisible(false)}
                className="bg-gray-500 text-white px-4 py-2 rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {sessions.map((session) => (
        <button
          key={session.id}
          onClick={() => setCurrentSessionId(session.id)}
          className={`px-4 py-2 rounded ${
            currentSessionId === session.id ? "bg-blue-500 text-white" : "bg-gray-200"
          }`}
        >
          {session.id}
        </button>
      ))}
    </div>
  );
};

export default ChatSidebar;
