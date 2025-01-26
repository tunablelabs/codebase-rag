"use client";

import { useState, FormEvent } from "react";
import Sidebar from "@/components/layout/Sidebar";
import MainContent from "@/components/layout/MainContent";
import { ChatOptions, Session } from "@/types";

export default function ChatPage() {
  const [chatOptions, setChatOptions] = useState<ChatOptions>({
    githubUrl: "",
    systemPrompt: "You are a coding assistant. Please answer the user's coding questions step by step, considering the code content and file structure. If unsure, say 'I don't know.'",
    astFlag: false,
    forceReindex: false,
    sessionId: undefined
  });

  const [files, setFiles] = useState<string[]>([]);
  const [isFilesVisible, setIsFilesVisible] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  const handleCreateSession = async (name: string, githubUrl: string): Promise<Session> => {
    try {
      const timestamp = new Date().toISOString();
      const newSession: Session = {
        id: Date.now().toString(),
        name,
        messages: [],
        createdAt: timestamp,
        lastActive: timestamp,
        githubUrl
      };
      
      setSessions(prev => [...prev, newSession]);
      setCurrentSessionId(newSession.id);
      setChatOptions(prev => ({
        ...prev,
        githubUrl,
        sessionId: newSession.id
      }));
      
      return newSession;
    } catch (error) {
      console.error("Failed to create session:", error);
      throw error;
    }
  };

  const handleFileUpload = async (fileList: FileList) => {
    try {
      const fileNames = Array.from(fileList).map(file => file.name);
      setFiles(fileNames);
      setIsFilesVisible(true);
  
      const folderPath = fileList[0].webkitRelativePath.split("/")[0];
      
      const formData = new FormData();
      Array.from(fileList).forEach(file => {
        formData.append("files", file);
      });
  
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });
  
      if (!response.ok) {
        throw new Error("Failed to upload files");
      }
  
      // will only create session after successfull upload
      return await handleCreateSession(folderPath, folderPath);
  
    } catch (error) {
      console.error("File upload failed:", error);
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const content = formData.get('message') as string;

    if (!currentSessionId) {
      alert("Please create a new session first.");
      return;
    }

    if (!content.trim()) {
      return;
    }

    try {
      const response = await fetch("/api/setup-query-engine", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          githubUrl: chatOptions.githubUrl,
          question: content,
          system_prompt: chatOptions.systemPrompt,
          ast_bool: chatOptions.astFlag,
          forceReindex: chatOptions.forceReindex,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to send message");
      }

      const timestamp = new Date().toISOString();
      const data = await response.json();

      setSessions(prev => prev.map(session => {
        if (session.id === currentSessionId) {
          return {
            ...session,
            messages: [
              ...session.messages,
              {
                type: "user",
                text: content,
                timestamp
              },
              {
                type: "bot",
                text: data.response || "No response received",
                timestamp
              }
            ],
            lastActive: timestamp
          };
        }
        return session;
      }));
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  const currentSession = sessions.find(s => s.id === currentSessionId);

  return (
    <div className="flex h-full max-w-[1920px] mx-auto">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onCreateSession={handleCreateSession}
        onSessionSelect={setCurrentSessionId}
        onFileUpload={handleFileUpload}
        setGithubUrl={(url) => setChatOptions(prev => ({ ...prev, githubUrl: url }))}
      />
      <MainContent
        currentSession={currentSession || null}
        isFilesVisible={isFilesVisible}
        files={files}
        isPending={false}
        chatOptions={chatOptions}
        onSubmit={handleSubmit}
        onPromptChange={(prompt) => setChatOptions(prev => ({ ...prev, systemPrompt: prompt }))}
        onResetPrompt={() => setChatOptions(prev => ({
          ...prev,
          systemPrompt: "You are a coding assistant. Please answer the user's coding questions step by step, considering the code content and file structure. If unsure, say 'I don't know.'"
        }))}
        onAstChange={() => setChatOptions(prev => ({ ...prev, astFlag: !prev.astFlag }))}
        onForceReindexChange={() => setChatOptions(prev => ({ ...prev, forceReindex: !prev.forceReindex }))}
      />
    </div>
  );
}