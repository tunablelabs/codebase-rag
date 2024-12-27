"use client";

import { FormEvent, useState } from "react";

export default function Chat() {
  const [githubUrl, setGithubUrl] = useState("");
  const [question, setQuestion] = useState("");
  const [system_prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [ast_bool, setAst] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const [files,setFiles]= useState<FileList | null>(null);
  const [foldername, setFolderName]= useState("");


  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setIsPending(true);
    setResponse("");

    if (githubUrl && !foldername) {
      // Check if the input is a valid GitHub URL
      if (!isValidGithubUrl(githubUrl)) {
        alert("Please provide a valid GitHub repository URL.");
        setIsPending(false);
        return
      }
    } else if (foldername && githubUrl) {
      setGithubUrl(foldername)
      console.log('recieved',githubUrl)
    } else {
      alert("Please provide either a GitHub URL or upload a folder.");
      setIsPending(false);
      return
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
      setGithubUrl("")
      setFolderName("")
    }
  }

  const isValidGithubUrl = (url) => {
    const regex = /^(https?:\/\/)?([a-zA-Z0-9-_]+)(?::([a-zA-Z0-9-_]+))?@github\.com\/([\w\-]+)\/([\w\-]+)/;
    return regex.test(url);
  };

  const handleChange = () => { 
    setAst(!ast_bool)
  }; 

  const handleFileChange = async(event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files;
    
    if (selectedFiles) {
      setFiles(selectedFiles);

      // Extract folder name from the first file's path
      const firstFile = selectedFiles[0];
      const folderPath = firstFile.webkitRelativePath.split('/')[0]; // Get the first part (folder name)
      console.log(folderPath)
      setFolderName(folderPath); // Set folder name
      const formData = new FormData();
      Array.from(selectedFiles).forEach((file) => {
        formData.append('files', file);
        });

      formData.append('directoryName', folderPath)
      setGithubUrl(folderPath)
      try {
        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        });
        const result = await response.json();
        console.log('Upload result:', result);
      } catch (error) {
        console.error('Error uploading files:', error);
      }
  
    }
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
          className="flex w-full max-w-3xl flex-col space-y-4">
            
          <fieldset className="flex flex-col space-y-2">
          <div className="flex items-center space-x-1">
            <input
              placeholder="GitHub Repository URL or Upload the folder"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              className="input input-bordered input-md w-[700px]"
            />
            <label htmlFor="file-upload" className="btn btn-neutral cursor-pointer">
              Upload Folder
            </label>
            <input
              type="file"
              id="file-upload"
              webkitdirectory="true"
              className="hidden"
              onChange={handleFileChange}
            />
    
            </div>
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
            <span className="label-text">Include AST? </span>
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
