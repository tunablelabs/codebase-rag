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
  const { sessions, currentSessionId, email, createSession, setSessions, currentSession, addMessageToSession, updateSessionMessage } = useSessionContext();

  const [limitReachedMessage, setLimitReachedMessage] = useState<string | null>(null);

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
          console.log(currentSessionId,'calling stats')
          const updatedStats = await api.getStats(currentSessionId, email);
          console.log(updatedStats)
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

  // const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
  //   e.preventDefault();
  //   setIsPending(true);
  //   const formData = new FormData(e.currentTarget);
  //   const content = formData.get('message') as string;

  //   const astFlagValue = chatOptions.astFlag ? "True" : "False";
  //   const llmEvaluatorValue = chatOptions.llmEvaluator ? "True" : "False";
  //   const prompt = chatOptions.systemPrompt;
  //   console.log('prompt',prompt)
  //   console.log(content,currentSessionId,astFlagValue,llmEvaluatorValue);
  //   if (!currentSessionId) {
  //     alert("Please create a new session first.");
  //     setIsPending(false);
  //     return;
  //   }

  //   if (!content.trim()) {
  //     return;
  //   }
  //   addMessageToSession(currentSessionId, {
  //     type: "user",
  //     text: content
  //   });


  //   try {
  //     const queryRequest: QueryRequest = {
  //       user_id: email,
  //       session_id: currentSessionId,
  //       use_llm: llmEvaluatorValue,
  //       ast_flag: astFlagValue,
  //       query: content,
  //       sys_prompt: prompt,
  //       limit: 5, // You can modify this limit as needed
  //     };

  //     const response = await fetch(`https://localhost:8000/api/codex/query/stream`, {
  //       method: "POST",
  //       headers: { "Content-Type": "application/json" },
  //       body: JSON.stringify(queryRequest),
  //     });

  //     if (!response.body) throw new Error("No response body received");

  //     const reader = response.body.getReader();
  //     const decoder = new TextDecoder();
  //     let botMessage = "";

  //     while (true) {
  //       const { done, value } = await reader.read();
  //       if (done) break;
  //       botMessage += decoder.decode(value, { stream: true });

  //       addMessageToSession(currentSessionId, {
  //         type: "bot",
  //         text: botMessage,
  //       });
  //     }
  //     setIsPending(false);
  //     setIsFilesVisible(true);

  //     /*const response = await api.queryRepository(queryRequest);
  //     console.log(response);
  //     setIsPending(false);
  //     setIsFilesVisible(true);

  //     addMessageToSession(currentSessionId, {
  //       type: "bot",
  //       text: response.response,
  //       metric: response.metric // ✅ Attach metrics
  //     });*/
  //   } catch (error) {
  //     console.error("Failed to send message:", error);
  //     setIsPending(false);
  //   }
  // };

  // const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
  //   e.preventDefault();
  //   setIsPending(true);
  //   const formData = new FormData(e.currentTarget);
  //   const content = formData.get('message') as string;

  //   const astFlagValue = chatOptions.astFlag ? "True" : "False";
  //   const llmEvaluatorValue = chatOptions.llmEvaluator ? "True" : "False";
  //   const prompt = chatOptions.systemPrompt;

  //   if (!currentSessionId) {
  //     alert("Please create a new session first.");
  //     setIsPending(false);
  //     return;
  //   }

  //   if (!content.trim()) {
  //     return;
  //   }

  //   // Add user message to the session
  //   addMessageToSession(currentSessionId, {
  //     type: "user",
  //     text: content
  //   });

  //   // Create a placeholder for the bot response
  //   addMessageToSession(currentSessionId, {
  //     type: "bot",
  //     text: "",
  //   });

  //   try {
  //     // Prepare the query request
  //     const queryRequest: QueryRequest = {
  //       user_id: email,
  //       session_id: currentSessionId,
  //       use_llm: llmEvaluatorValue,
  //       ast_flag: astFlagValue,
  //       query: content,
  //       sys_prompt: prompt,
  //       limit: 5,
  //     };

  //     // Create WebSocket connection
  //     const ws = new WebSocket(`ws://localhost:8000/api/codex/query/stream`);

  //     // Initialize bot message
  //     let botMessage = "";
  //     // Define metrics interface using QueryMetrics from types
  //     let currentMetrics: undefined = undefined;

  //     // Handle WebSocket open event - send the query
  //     ws.onopen = () => {
  //       console.log("WebSocket connection established");
  //       ws.send(JSON.stringify(queryRequest));
  //     };

  //     // Handle incoming messages
  //     ws.onmessage = (event) => {
  //       const data = JSON.parse(event.data);

  //       // Check for errors
  //       if (data.error) {
  //         console.error("WebSocket error:", data.error);
  //         addMessageToSession(currentSessionId, {
  //           type: "bot",
  //           text: `Error: ${data.error}`,
  //         });
  //         ws.close();
  //         return;
  //       }

  //       // Handle partial responses
  //       if (data.partial_response) {
  //         botMessage += data.partial_response;
  //         addMessageToSession(currentSessionId, {
  //           type: "bot",
  //           text: botMessage,
  //           metric: currentMetrics,
  //         });
  //       }

  //       // Save metrics if provided
  //       if (data.metric) {
  //         currentMetrics = data.metric;
  //         addMessageToSession(currentSessionId, {
  //           type: "bot",
  //           text: botMessage,
  //           metric: currentMetrics,
  //         });
  //       }

  //       // If streaming is complete, close the connection
  //       if (data.complete) {
  //         ws.close();
  //       }
  //     };

  //     // Handle WebSocket errors
  //     ws.onerror = (error) => {
  //       console.error("WebSocket error:", error);
  //       addMessageToSession(currentSessionId, {
  //         type: "bot",
  //         text: botMessage + "\n\nConnection error occurred.",
  //         metric: currentMetrics,
  //       });
  //       setIsPending(false);
  //     };

  //     // Handle WebSocket close
  //     ws.onclose = () => {
  //       console.log("WebSocket connection closed");
  //       setIsPending(false);
  //       setIsFilesVisible(true);
  //     };

  //   } catch (error) {
  //     console.error("Failed to send message:", error);
  //     setIsPending(false);
  //   }
  // };

//  Claude 3.7 code here

const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  setIsPending(true);
  setLimitReachedMessage(null); // Clear any prior message

  const formData = new FormData(e.currentTarget);
  const content = formData.get('message') as string;

  const astFlagValue = chatOptions.astFlag ? "True" : "False";
  const llmEvaluatorValue = chatOptions.llmEvaluator ? "True" : "False";
  const prompt = chatOptions.systemPrompt;

  if (!currentSessionId) {
    alert("Please create a new session first.");
    setIsPending(false);
    return;
  }

  if (!content.trim()) {
    return;
  }

  // Add user message to the session
  addMessageToSession(currentSessionId, {
    type: "user",
    text: content
  });

  // Add a single bot message that we'll update as streaming occurs
  const botMessageId = Date.now().toString(); // Create a unique ID for this message

  // Add initial empty bot message
  addMessageToSession(currentSessionId, {
    id: botMessageId,
    type: "bot",
    text: "",
  });

  try {
    // Prepare the query request
    const queryRequest: QueryRequest = {
      user_id: email,
      session_id: currentSessionId,
      use_llm: llmEvaluatorValue,
      ast_flag: astFlagValue,
      query: content,
      sys_prompt: prompt,
      limit: 5,
    };

    // Create WebSocket connection
    // const BASE_URL = process.env.NEXT_PUBLIC_URL || 'http://localhost:8000';
    const BASE_URL = 'https://codebase-rag-production.up.railway.app'
    const wsProtocol = BASE_URL.startsWith('https') ? 'wss' : 'ws';
    const wsUrl = BASE_URL.replace(/^http(s)?:\/\//, '');
    const ws = new WebSocket(`${wsProtocol}://${wsUrl}/api/codex/query/stream`);

    // Initialize bot message
    let botMessage = "";
    // Define metrics interface using QueryMetrics from types
    let currentMetrics :any = undefined;

    // Handle WebSocket open event - send the query
    ws.onopen = () => {
      console.log("WebSocket connection established");
      ws.send(JSON.stringify(queryRequest));
    };

    // Handle incoming messages
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // Check for errors
      if (data.error) {
        console.error("WebSocket error:", data.error);
        // Update the existing bot message with the error
        updateSessionMessage(currentSessionId, botMessageId, {
          type: "bot",
          text: `Error: ${data.error}`,
        });
        ws.close();
        return;
      }
       if (data.limit_reached) {
          console.warn("User has reached daily limit:", data.message);

          // Show the message in UI
          setLimitReachedMessage(data.message || "You have reached your daily limit.");
          setIsPending(false);

          // Optionally update the last bot message or create a new one
          updateSessionMessage(currentSessionId, botMessageId, {
            type: "bot",
            text: data.message || "You have reached your daily limit.",
          });

          ws.close();
          return;
        }

      // Handle partial responses
      if (data.partial_response) {
        botMessage += data.partial_response;
        // Update the existing message instead of adding a new one
        updateSessionMessage(currentSessionId, botMessageId, {
          type: "bot",
          text: botMessage,
          metric: currentMetrics,
        });
      }

      // Save metrics if provided
      if (data.metric) {
        currentMetrics = data.metric;
        // Update the existing message with new metrics
        updateSessionMessage(currentSessionId, botMessageId, {
          type: "bot",
          text: botMessage,
          metric: currentMetrics,
        });
      }

      // If streaming is complete, close the connection
      if (data.complete) {
        ws.close();
      }
    };

    // Handle WebSocket errors
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      // Update the existing message with the error
      updateSessionMessage(currentSessionId, botMessageId, {
        type: "bot",
        text: botMessage + "\n\nConnection error occurred.",
        metric: currentMetrics,
      });
      setIsPending(false);
    };

    // Handle WebSocket close
    ws.onclose = () => {
      console.log("WebSocket connection closed");
      setIsPending(false);
      setIsFilesVisible(true);
    };

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
      {/* 3) Example UI banner if user has exceeded daily limit */}
      {limitReachedMessage && (
        <div className="absolute top-0 left-0 right-0 bg-red-500 text-white p-4 text-center">
          {limitReachedMessage}
        </div>
      )}
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

