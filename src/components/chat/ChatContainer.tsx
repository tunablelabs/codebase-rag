import { useState, FormEvent } from 'react';
import ChatForm from './ChatForm';
import ChatWindow from './ChatWindow';
import FileList from '../file/FileList';

interface Message {
  type: 'user' | 'bot';
  text: string;
}

interface Session {
  id: string;
  messages: Message[];
}

interface ChatContainerProps {
  currentSession: Session | null;
  githubUrl: string;
  setGithubUrl: (url: string) => void;
  system_prompt: string;
  setPrompt: (prompt: string) => void;
  ast_bool: boolean;
  setAst: (value: boolean) => void;
  forceReindex: boolean;
  setForceReindex: (value: boolean) => void;
  setResponses: (responses: Message[]) => void;
}

export default function ChatContainer({
  currentSession,
  githubUrl,
  setGithubUrl,
  system_prompt,
  setPrompt,
  ast_bool,
  setAst,
  forceReindex,
  setForceReindex,
  setResponses
}: ChatContainerProps) {
  const [isPending, setIsPending] = useState(false);
  const [question, setQuestion] = useState("");
  const [isFilesVisible, setIsFilesVisible] = useState(false);
  const [files, setFiles] = useState<string[]>([]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!currentSession) {
      alert("Please create a new session first.");
      return;
    }

    setIsPending(true);

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
        throw new Error('Failed to get response');
      }

      setResponses(prev => [...prev, { type: 'user', text: question }]);
      const data = await res.json();
      setResponses(prev => [...prev, { type: 'bot', text: data.response || 'No response received' }]);
      setQuestion("");
    } catch (error) {
      setResponses(prev => [...prev, { type: 'bot', text: 'Error fetching response' }]);
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div className="flex">
      <div className="w-5/6 mx-auto max-w-5xl space-y-6">
        <ChatWindow 
          messages={currentSession?.messages || []} 
          isPending={isPending} 
        />
        <ChatForm
          question={question}
          setQuestion={setQuestion}
          system_prompt={system_prompt}
          setPrompt={setPrompt}
          ast_bool={ast_bool}
          setAst={setAst}
          forceReindex={forceReindex}
          setForceReindex={setForceReindex}
          onSubmit={handleSubmit}
          isPending={isPending}
        />
      </div>
      <div className="w-1/6 p-6 space-y-4">
        <FileList isFilesVisible={isFilesVisible} files={files} />
      </div>
    </div>
  );
}