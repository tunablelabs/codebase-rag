"use client";

import { useState, FormEvent } from "react";

interface ChatFormProps {
  githubUrl: string;
  setGithubUrl: (url: string) => void;
  setResponses: (responses: { type: "user" | "bot"; text: string }[]) => void;
  system_prompt: string;
  setPrompt: (prompt: string) => void;
  ast_bool: boolean;
  setAst: (value: boolean) => void;
  forceReindex: boolean;
  setForceReindex: (value: boolean) => void;
  currentSessionId: string | null;
  setSessions: (
    updater: (prevSessions: {
      id: string;
      messages: { type: "user" | "bot"; text: string }[];
    }[]) => { id: string; messages: { type: "user" | "bot"; text: string }[] }[]
  ) => void;
}

export default function ChatForm({
  githubUrl,
  setGithubUrl,
  setResponses,
  system_prompt,
  setPrompt,
  ast_bool,
  setAst,
  forceReindex,
  setForceReindex,
  currentSessionId,
  setSessions,
}: ChatFormProps) {
  const [question, setQuestion] = useState("");
  const [isPending, setIsPending] = useState(false);

  const isValidGithubUrl = (url: string) => {
    const regex =
      /^(https?:\/\/)?([a-zA-Z0-9-_]+)?(?::([a-zA-Z0-9-_]+))?@?github\.com\/([\w\-]+)\/([\w\-]+)/;
    return regex.test(url);
  };

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!currentSessionId) {
      alert("Please create a new session first.");
      return;
    }

    setIsPending(true);

    if (githubUrl) {
      if (!isValidGithubUrl(githubUrl)) {
        alert("Please provide a valid GitHub repository URL.");
        setIsPending(false);
        return;
      }
    } else {
      alert("Please provide a GitHub URL.");
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
      setResponses((prevResponses) => [...prevResponses, { type: "bot", text: newResponse }]);

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
      setResponses((prevResponses) => [...prevResponses, { type: "bot", text: "Error fetching response" }]);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-6 bg-white rounded-lg shadow">
      <input
        type="text"
        placeholder="GitHub Repository URL"
        value={githubUrl}
        onChange={(e) => setGithubUrl(e.target.value)}
        className="w-full p-2 border rounded"
      />
      <input
        type="text"
        placeholder="Enter your question"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        className="w-full p-2 border rounded"
        required
      />
      <textarea
        placeholder="System prompt"
        value={system_prompt}
        onChange={(e) => setPrompt(e.target.value)}
        className="w-full p-2 border rounded"
      />
      <div className="flex gap-4">
        <label>
          <input type="checkbox" checked={ast_bool} onChange={() => setAst(!ast_bool)} /> Include AST
        </label>
        <label>
          <input type="checkbox" checked={forceReindex} onChange={() => setForceReindex(!forceReindex)} /> Force Reindex
        </label>
      </div>
      <button
        type="submit"
        disabled={isPending}
        className="w-full p-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        {isPending ? "Processing..." : "Submit"}
      </button>
    </form>
  );
}
