"use client";

import { useState, FormEvent, useEffect, useCallback } from "react";
import Sidebar from "@/components/layout/Sidebar";
import MainContent from "@/components/layout/MainContent";
import { ChatOptions, Session } from "@/types";
import { useSessionContext } from "@/context/SessionProvider";
import api from "@/services/api";
import { QueryRequest, QueryResponse } from "@/types";

export default function ChatPage() {
  const [chatOptions, setChatOptions] = useState<ChatOptions>({
    githubUrl: "",
    systemPrompt: "",
    astFlag: false,
    forceReindex: false,
    sessionId: undefined,
    llmEvaluator:false 
  });

  interface Stats {
    total_code_files: number;
    language_distribution: {
      [language: string]: string; 
    };
  }

  const [files, setFiles] = useState<string[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [isFilesVisible, setIsFilesVisible] = useState(false);
  const [isStatsVisible, setIsStatsVisible] = useState(false);
  const { sessions, currentSessionId, createSession, setSessions, currentSession, addMessageToSession } = useSessionContext();
  
  const handlestatsUpload = useCallback((stats: Stats) => {
    console.log('handle stats upload invoked', stats)
    setIsStatsVisible(true);
    setStats(stats);
    console.log(stats.total_code_files, stats.language_distribution)
  }, []);
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
  
    } catch (error) {
      console.error("File upload failed:", error);
    }
  };
  
  // Add this useEffect to handle stats updates
  useEffect(() => {
    const updateStatsForSession = async () => {
      if (currentSessionId) {
        try {
          const updatedStats = await api.getStats(currentSessionId);
          handlestatsUpload(updatedStats.stats);
          setIsStatsVisible(true);
        } catch (error) {
          console.error("Failed to fetch stats for session:", error);
          setStats(null);
          setIsStatsVisible(false);
        }
      } else {
        setStats(null);
        setIsStatsVisible(false);
      }
    };

    updateStatsForSession();
  }, [currentSessionId, handlestatsUpload]);
  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsPending(true);
    const formData = new FormData(e.currentTarget);
    const content = formData.get('message') as string;
    
    const astFlagValue = chatOptions.astFlag ? "True" : "False";
    const llmEvaluatorValue = chatOptions.llmEvaluator ? "True" : "False";
    const prompt = chatOptions.systemPrompt;
    console.log('prompt',prompt)
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
        sys_prompt: prompt,
        limit: 5, // You can modify this limit as needed
      };

      const response = await api.queryRepository(queryRequest);
      console.log(response);
      setIsPending(false);
      setIsFilesVisible(true);

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
          systemPrompt: ""
        }))}
        onAstChange={() => setChatOptions(prev => ({ ...prev, astFlag: !prev.astFlag }))}
        onForceReindexChange={() => setChatOptions(prev => ({ ...prev, forceReindex: !prev.forceReindex }))}
        onLlmEvaluator={() => setChatOptions(prev => ({ ...prev, llmEvaluator: !prev.llmEvaluator})) }
      />
    </div>
  );
}
