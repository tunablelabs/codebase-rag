"use client";

import { FormEvent, useState } from "react";

export default function Chat() {
  const [githubUrl, setGithubUrl] = useState("");
  const [question, setQuestion] = useState("");
  const [system_prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [ast_bool, setAst] = useState(false);
  const [isPending, setIsPending] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();

    setIsPending(true);
    setResponse("");
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
          ast_bool
        }),
      });
      console.log('done')
      if (!res.ok) {
        // Ensure proper error handling
        const errorData = await res.json();
        throw new Error(errorData.message || "Something went wrong");
      }

      const data = await res.json();
      setResponse(data.response || "No response received");
    } catch (error: any) {
      setResponse(error.message || "Error occurred while fetching data.");
    } finally {
      setIsPending(false);
    }
  }

  const handleChange = () => { 
    setAst(!ast_bool)
  }; 

  return (
    <>
      {/* Added aria-live for better accessibility */}
      <div
        className="flex h-0 grow flex-col-reverse overflow-y-scroll"
        aria-live="polite"
      >
        <div className="space-y-4 py-8">
          {response && (
            <div className="mx-auto flex max-w-3xl whitespace-pre-wrap">
              <div className="rounded bg-gray-100 p-4">{response}</div>
            </div>
          )}
        </div>
      </div>

      <div className="mb-8 flex justify-center gap-2">
        <form
          onSubmit={handleSubmit}
          className="flex w-full max-w-3xl flex-col space-y-4"
        >
          <fieldset className="flex flex-col space-y-2">
            <input
              placeholder="GitHub Repository URL or Full Repo Path"
              required
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              className="input input-bordered input-sm"
            />
            <textarea
              placeholder="Enter the system prompt"
              required
              value="You are a coding assistant. Please answer the user's coding questions step by step, considering the code content and file structure. If unsure, say 'I don't know."
              onChange={(e) => setPrompt(e.target.value)}
              className="textarea textarea-bordered textarea-sm"
            />
            <input
              placeholder="Enter your question about the code"
              required
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="input input-bordered input-md"
            />
           

            <label className="flex items-center space-x-3">
            <span className="label-text">Include ast to answer the question? </span>
            <input
              name="ast_name"
              type="checkbox"
              className="checkbox"
              onChange={handleChange}
            />
            </label>
             
          </fieldset>
          <button
            className="btn btn-neutral"
            type="submit"
            disabled={isPending}
          >
            {isPending ? "Processing..." : "Submit"}
          </button>
        </form>
      </div>
    </>
  );
}
