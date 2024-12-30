"use client";

import { FormEvent, useState } from "react";

export default function Chat() {
  const defaultPrompt =
    "You are a coding assistant. Please answer the user's coding questions step by step, considering the code content and file structure. If unsure, say 'I don't know.'";
  const [githubUrl, setGithubUrl] = useState("");
  const [question, setQuestion] = useState("");
  const [system_prompt, setPrompt] = useState(defaultPrompt);
  const [response, setResponse] = useState("");
  const [ast_bool, setAst] = useState(false);
  const [forceReindex, setForceReindex] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const [files, setFiles] = useState<FileList | null>(null);
  const [foldername, setFolderName] = useState("");

  const resetPrompt = () => {
    setPrompt(defaultPrompt);
  };

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsPending(true);
    setResponse("");

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

      const data = await res.json();
      setResponse(data.response || "No response received");
    } catch (error: any) {
      setResponse(error.message || "Error occurred while fetching data.");
    } finally {
      setIsPending(false);
      setGithubUrl("");
      setFolderName("");
    }
  }

  const isValidGithubUrl = (url: string) => {
    const regex =
      /^(https?:\/\/)?([a-zA-Z0-9-_]+)(?::([a-zA-Z0-9-_]+))?@github\.com\/([\w\-]+)\/([\w\-]+)/;
    return regex.test(url);
  };

  const handleAstChange = () => {
    setAst(!ast_bool);
  };

  const handleForceReindexChange = () => {
    setForceReindex(!forceReindex);
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;

    if (selectedFiles) {
      setFiles(selectedFiles);

      const firstFile = selectedFiles[0];
      const folderPath = firstFile.webkitRelativePath.split("/")[0];
      setFolderName(folderPath);

      const formData = new FormData();
      Array.from(selectedFiles).forEach((file) => {
        formData.append("files", file);
      });

      formData.append("directoryName", folderPath);
      setGithubUrl(folderPath);

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
    <div className="mx-auto w-full max-w-5xl space-y-6">
      {/* Form Section */}
      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl bg-white/70 p-6 shadow-lg backdrop-blur-sm dark:bg-slate-900/70"
      >
        {/* GitHub URL and File Upload */}
        <div className="flex gap-2">
          <input
            placeholder="GitHub Repository URL"
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
            className="flex-1 rounded-lg border border-slate-200 bg-white px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-900"
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

        {/* Question Input */}
        <input
          placeholder="Enter your question about the code"
          required
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-900"
        />

        {/* System Prompt */}
        <div className="space-y-2">
          <textarea
            placeholder="Enter the system prompt"
            value={system_prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="min-h-[100px] w-full resize-y rounded-lg border border-slate-200 bg-white px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-900"
          />
          <button
            type="button"
            onClick={resetPrompt}
            className="mt-2 inline-block transform rounded-md bg-blue-100 px-4 py-2 text-sm font-medium text-blue-600 shadow-sm transition-transform hover:scale-105 hover:bg-blue-200 dark:bg-blue-800 dark:text-blue-300 dark:hover:bg-blue-700"
          >
            Reset to Default Prompt
          </button>
        </div>

        {/* Options */}
        <div className="flex gap-6">
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

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isPending}
          className="w-full rounded-lg bg-blue-600 px-6 py-2 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isPending ? "Processing..." : "Submit"}
        </button>
      </form>

      {/* Response Section */}
      <div
        className="min-h-[400px] rounded-xl bg-white/70 p-6 shadow-lg backdrop-blur-sm dark:bg-slate-900/70"
        aria-live="polite"
      >
        {response ? (
          <pre className="whitespace-pre-wrap font-mono text-sm text-slate-800 dark:text-slate-200">
            {response}
          </pre>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400 dark:text-slate-500">
            Your response will appear here
          </div>
        )}
      </div>
    </div>
  );
}
