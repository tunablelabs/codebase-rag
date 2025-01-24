"use client";

import { FormEvent, useState } from "react";
import ChatSidebar from "./components/ChatSidebar";
import ChatForm from "./components/ChatForm";
import ChatWindow from "./components/ChatWindow";
import FileList from "./components/FileList";

export default function Chat() {
  const defaultPrompt =
    "You are a coding assistant. Please answer the user's coding questions step by step, considering the code content and file structure. If unsure, say 'I don't know.'";
  const [githubUrl, setGithubUrl] = useState("");
  const [question, setQuestion] = useState("");
  const [system_prompt, setPrompt] = useState(defaultPrompt);
  const [response, setResponses] = useState<{ type: "user" | "bot"; text: string }[]>([]);
  const [ast_bool, setAst] = useState(false);
  const [forceReindex, setForceReindex] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const [files, setFiles] = useState([]);
  const [foldername, setFolderName] = useState("");
  const [isFilesVisible, setIsFilesVisible] = useState(false);
  const [sessions, setSessions] = useState<{ id: string; messages: { type: "user" | "bot"; text: string }[] }[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  const createNewSession = (name: string) => {
    const newSession = {
      id: name,
      messages: [],
    };
    setSessions([...sessions, newSession]);
    setCurrentSessionId(newSession.id);
  };
  
  

  const resetPrompt = () => {
    setPrompt(defaultPrompt);
  };

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!currentSessionId) {
      alert("Please create a new session first.");
      return;
    }
  
    setIsPending(true);
    //setResponse("");

    if (githubUrl && !foldername) {
      if (!isValidGithubUrl(githubUrl)) {
        alert("Please provide a valid GitHub repository URL.");
        setIsPending(false);
        return;
      }
    } else if (foldername && githubUrl) {
      setGithubUrl(foldername);
    } else {
      alert("Please provide either a GitHub URL or upload a folder.");
      setIsPending(false);
      return;
    }

    try {
      const res = await fetch("/api/setup-query-engine", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          githubUrl,
          question,
          system_prompt,
          ast_bool,
          forceReindex,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.message || "Something went wrong");
      }
      setResponses((prevResponses) => [...prevResponses, { type: "user", text: question }]);
      const data = await res.json();
      const newResponse = data.response || "No response received";
      setResponses((prevResponses) =>[...prevResponses, { type: "bot", text: newResponse }]);

      setSessions((prevSessions) =>
        prevSessions.map((session) =>
          session.id === currentSessionId
            ? {
                ...session,
                messages: [
                  ...session.messages,
                  { type: "user", text: question },
                  { type: "bot", text: newResponse },
                ],
              }
            : session
        )
      );
    } catch (error: any) {
      setResponses((prevResponses) => [...prevResponses, { type: "bot", text:"Error fetching response"}]);
    } finally {
      setIsPending(false);
      //setGithubUrl("");
      //setFolderName("");
    }
  }

  const isValidGithubUrl = (url: string) => {
    const regex =
      /^(https?:\/\/)?([a-zA-Z0-9-_]+)?(?::([a-zA-Z0-9-_]+))?@?github\.com\/([\w\-]+)\/([\w\-]+)/;
    return regex.test(url);
  };

  const handleAstChange = () => {
    setAst(!ast_bool);
  };

  const handleForceReindexChange = () => {
    setForceReindex(!forceReindex);
  };

  const currentSession = sessions?.find((session) => session.id === currentSessionId);
  return (
    
    <div className="flex">

        <ChatSidebar
        sessions={sessions}
        createNewSession={createNewSession}
        setCurrentSessionId={setCurrentSessionId}
        currentSessionId={currentSessionId}
        setFiles={setFiles}
        setFolderName={setFolderName}
        setIsFilesVisible={setIsFilesVisible}
        setGithubUrl={setGithubUrl}
        />

        <div className="w-5/6 mx-auto max-w-5xl space-y-6">
          {/* Form Section */}
          <form
            onSubmit={handleSubmit}
            className="space-y-1 rounded-xl bg-white/70 p-6 shadow-lg backdrop-blur-sm dark:bg-slate-900/70"
          >  
            {/* Response Section */}
            <div
              className="min-h-[360px] grow max-h-[320px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-500 scrollbar-track-gray-200 dark:scrollbar-thumb-gray-700 dark:scrollbar-track-gray-900 rounded-xl bg-white/70 p-6 shadow-lg backdrop-blur-sm dark:bg-slate-900/70"
              aria-live="polite"
              style={{ maxHeight: "400px" }} 
            >
              {currentSession?.messages.length > 0 ? (
                <div className="space-y-2">
                  {currentSession.messages.map((msg, index) => (
                    <div key={index} className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}>
                      <pre className={`whitespace-pre-wrap p-3 rounded-lg ${msg.type === "user" ? "bg-blue-500 text-white" : "bg-gray-200 text-gray-800"}`}>
                        {msg.text}
                      </pre>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-400">Your response will appear here</div>
              )}
            </div>

            {/* Question Input */}
            <input
              placeholder="Enter your question about the code"
              required
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-900"
            />

            {/* System Prompt */}
            <div className="space-y-1">
              <textarea
                placeholder="Enter the system prompt"
                value={system_prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="min-h-[50px] w-full resize-y rounded-lg border border-slate-200 bg-white px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-900"
              />
              
              {/* Options */}
              <div className="flex gap-6">
                <button
                  type="button"
                  onClick={resetPrompt}
                  className="mt-2 inline-block transform rounded-md bg-blue-100 px-4 py-2 text-sm font-medium text-blue-600 shadow-sm transition-transform hover:scale-105 hover:bg-blue-200 dark:bg-blue-800 dark:text-blue-300 dark:hover:bg-blue-700"
                >
                  Reset to Default Prompt
                </button>
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 dark:border-slate-700"
                    onChange={handleAstChange}
                  />
                  <span className="text-slate-700 dark:text-slate-300">Include AST</span>
                </label>
                <label className="inline-flex items-center gap-2">
                  <input
                    type="checkbox"
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 dark:border-slate-700"
                    onChange={handleForceReindexChange}
                  />
                  <span className="text-slate-700 dark:text-slate-300">Force Reindex</span>
                </label>
              </div>
            </div>


            {/* Submit Button */}
            <button
              type="submit"
              disabled={isPending}
              className="w-full rounded-lg bg-blue-600 px-6 py-2 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isPending ? "Processing..." : "Submit"}
            </button>
          </form>

        
        </div>
      <div className="w-1/6 p-6 space-y-4">
        <FileList isFilesVisible={isFilesVisible} files={files} />
      </div>
    </div>
  );
}
