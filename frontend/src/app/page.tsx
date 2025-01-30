"use client";

import { useState, FormEvent } from "react";
import Sidebar from "@/components/layout/Sidebar";
import MainContent from "@/components/layout/MainContent";
import { ChatOptions, Session } from "@/types";
//import { useSession } from "@/hooks/useSession";
import { useSessionContext } from "@/context/SessionProvider";
import { useFileUpload } from "@/hooks/useFileUpload"
import api from "@/services/api";
import { QueryRequest, QueryResponse } from "@/types";

export default function ChatPage() {
  const [chatOptions, setChatOptions] = useState<ChatOptions>({
    githubUrl: "",
    systemPrompt: "You are a coding assistant. Please answer the user's coding questions step by step, considering the code content and file structure. If unsure, say 'I don't know.'",
    astFlag: false,
    forceReindex: false,
    sessionId: undefined,
    llmEvaluator:false 
  });

  interface Stats {
    total_code_files: number;
    language_distribution: {
      [language: string]: string; // For example: {"Python": "100%"}
    };
  }

  const [files, setFiles] = useState<string[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [isFilesVisible, setIsFilesVisible] = useState(false);
  const [isStatsVisible, setIsStatsVisible] = useState(false);
  const { sessions, currentSessionId, createSession, setSessions, currentSession, updateSession, addMessageToSession } = useSessionContext();
  const handlestatsUpload = async(stats: Stats)=>{
    console.log('handle stats upload invoked', stats)
    setIsStatsVisible(true);
    setStats(stats);
    console.log(stats.total_code_files, stats.language_distribution)
  };
  const handleFileUpload = async (fileList: FileList) => {
    try {
      const folderSet = new Set<string>();
      Array.from(fileList).forEach(file => {
        const pathParts = file.webkitRelativePath.split("/"); // Split the path by "/"
        if (pathParts.length > 1) {
          folderSet.add(pathParts[0]); // Add only the top-level folder
        }
      });

      const uniqueFolders = Array.from(folderSet);
      //const fileNames = Array.from(fileList).map((file) => file.webkitRelativePath || file.name); 
      setFiles(uniqueFolders);
      setIsFilesVisible(true);
  
      /*const folderPath = fileList[0].webkitRelativePath.split("/")[0];
      const formData = new FormData();
      Array.from(fileList).forEach((file) => {
        console.log(file)
        formData.append("files", file);
      });
      formData.append("", folderPath);
      const response = await fetch("http://127.0.0.1:8000/upload-folder/", {
        method: "POST",
        body: formData
      });
      const result = await response.json();
      console.log(result) */
  
    } catch (error) {
      console.error("File upload failed:", error);
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsPending(true);
    const formData = new FormData(e.currentTarget);
    const content = formData.get('message') as string;
    
    const astFlagValue = chatOptions.astFlag ? "True" : "False";
    const llmEvaluatorValue = chatOptions.llmEvaluator ? "True" : "False";
    console.log(content,currentSessionId,astFlagValue,llmEvaluatorValue);
    if (!currentSessionId) {
      alert("Please create a new session first.");
      return;
    }

    if (!content.trim()) {
      return;
    }
    addMessageToSession(currentSessionId, {
      type: "user",
      text: content
    });
   

    try {
      const queryRequest: QueryRequest = {
        file_id: currentSessionId,
        use_llm: llmEvaluatorValue, 
        ast_flag: astFlagValue,
        query: content,
        limit: 3, // You can modify this limit as needed
      };

      const response = await api.queryRepository(queryRequest);
      console.log(response);
      setIsPending(false);
      setIsFilesVisible(true);

      const timestamp = new Date().toISOString();
      const data = response.response;
      addMessageToSession(currentSessionId, {
        type: "bot",
        text: response.response,
        metric: response.metric // ✅ Attach metrics
      });
    } catch (error) {
      console.error("Failed to send message:", error);
      setIsPending(false);
    }
  };


  return (
    <div className="flex h-full max-w-[1920px] mx-auto">
      <Sidebar
        onFileUpload={handleFileUpload}
        handlestatsUpload={handlestatsUpload}
      />
      <MainContent
        currentSession={currentSession || null}
        isFilesVisible={isFilesVisible}
        isStatsVisible={isStatsVisible}
        stats={stats}
        files={files}
        isPending={isPending}
        chatOptions={chatOptions}
        onSubmit={handleSubmit}
        onPromptChange={(prompt) => setChatOptions(prev => ({ ...prev, systemPrompt: prompt }))}
        onResetPrompt={() => setChatOptions(prev => ({
          ...prev,
          systemPrompt: "You are a coding assistant. Please answer the user's coding questions step by step, considering the code content and file structure. If unsure, say 'I don't know.'"
        }))}
        onAstChange={() => setChatOptions(prev => ({ ...prev, astFlag: !prev.astFlag }))}
        onForceReindexChange={() => setChatOptions(prev => ({ ...prev, forceReindex: !prev.forceReindex }))}
        onLlmEvaluator={() => setChatOptions(prev => ({ ...prev, llmEvaluator: !prev.llmEvaluator})) }
      />
    </div>
  );
}
