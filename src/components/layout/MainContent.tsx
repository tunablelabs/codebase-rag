import { FormEvent, useState } from "react";
import { FileListComponent } from "../file/FileList";
import { ChatOptions, Session } from "@/types";
import { Settings, Send, ChevronUp, ChevronDown } from 'lucide-react';

interface MainContentProps {
  currentSession: Session | null;
  isFilesVisible: boolean;
  files: string[];
  isPending: boolean;
  chatOptions: ChatOptions;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  onPromptChange: (prompt: string) => void;
  onResetPrompt: () => void;
  onAstChange: () => void;
  onForceReindexChange: () => void;
}

export default function MainContent({
  currentSession,
  isFilesVisible,
  files,
  isPending,
  chatOptions,
  onSubmit,
  onPromptChange,
  onResetPrompt,
  onAstChange,
  onForceReindexChange,
}: MainContentProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <div className="flex flex-1">
      <div className="flex-1 p-2">
        <div className="max-w-4xl mx-auto space-y-2">
        
          <div className="h-[calc(100vh-220px)] rounded-xl bg-base-200/50 dark:bg-base-300/20 
            shadow-lg backdrop-blur-sm transition-all duration-300 
            border border-base-300 dark:border-slate-600/50">
            <div className="h-full overflow-y-auto pr-2 
              scrollbar-thin scrollbar-thumb-base-300 hover:scrollbar-thumb-base-400 
              dark:scrollbar-thumb-slate-600 dark:hover:scrollbar-thumb-slate-500">
              <div className="h-full p-4 space-y-4">
                {currentSession?.messages.length ? (
                  <div className="space-y-4">
                    {currentSession.messages.map((msg, index) => (
                      <div key={index} className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"} animate-fade-in`}>
                        <pre className={`whitespace-pre-wrap p-3 rounded-lg shadow-sm transition-all max-w-[80%] ${
                          msg.type === "user" 
                            ? "bg-primary text-primary-content" 
                            : "bg-base-100 dark:bg-base-200 text-base-content"
                        }`}>
                          {msg.text}
                        </pre>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center space-y-2">
                      <div className="text-4xl mb-2">💬</div>
                      <p className="text-base-content/60">Your response will appear here</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

 
          <div className="relative">
            <form onSubmit={onSubmit} className="relative">
              <div className={`
                absolute bottom-full left-0 right-0 mb-2
                bg-base-100 dark:bg-base-200
                rounded-xl shadow-lg
                border border-base-300 dark:border-slate-600/50
                transition-all duration-300
                ${isSettingsOpen ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'}
              `}>
                <div className="p-4 space-y-4">
                  <textarea
                    value={chatOptions.systemPrompt}
                    onChange={(e) => onPromptChange(e.target.value)}
                    className="w-full min-h-[100px] p-3 rounded-lg
                      bg-base-200 dark:bg-base-300
                      border border-base-300 dark:border-slate-600/50
                      text-base-content placeholder:text-base-content/50
                      focus:ring-2 focus:ring-primary/50 focus:border-transparent
                      resize-none transition-all duration-300"
                    placeholder="Configure how the AI should behave..."
                  />

                  <div className="flex items-center justify-between flex-wrap gap-4">
                    <button
                      type="button"
                      onClick={onResetPrompt}
                      className="px-3 py-2 text-sm font-medium
                        bg-primary/10 text-primary hover:bg-primary/20
                        rounded-lg transition-all duration-300"
                    >
                      Reset to Default
                    </button>

                    <div className="flex items-center gap-6">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={chatOptions.astFlag}
                          onChange={onAstChange}
                          className="checkbox checkbox-primary checkbox-sm"
                        />
                        <span className="text-sm text-base-content/80">Include AST</span>
                      </label>

                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={chatOptions.forceReindex}
                          onChange={onForceReindexChange}
                          className="checkbox checkbox-primary checkbox-sm"
                        />
                        <span className="text-sm text-base-content/80">Force Reindex</span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>

          
              <div className="relative flex items-center">
                <button
                  type="button"
                  onClick={() => setIsSettingsOpen(!isSettingsOpen)}
                  className="absolute left-4 p-2 text-base-content/50 
                    hover:text-base-content rounded-lg
                    hover:bg-base-200 dark:hover:bg-base-300
                    transition-all duration-300 group"
                >
                  <Settings className="w-5 h-5" />
                  {isSettingsOpen ? (
                    <ChevronDown className="w-4 h-4 absolute -right-5 top-1.5" />
                  ) : (
                    <ChevronUp className="w-4 h-4 absolute -right-5 top-1.5" />
                  )}
                </button>

                <input
                  name="message"
                  placeholder="Ask me about your code..."
                  className="w-full pl-16 pr-16 py-3.5 rounded-xl
                    bg-base-100 dark:bg-base-200
                    border border-base-300 dark:border-base-700
                    text-base-content placeholder:text-base-content/50
                    focus:outline-none focus:ring-2 focus:ring-primary/50
                    transition-all duration-300"
                  required
                />

                <button
                  type="submit"
                  disabled={isPending}
                  className="absolute right-4 p-2 
                    text-primary hover:text-primary-focus
                    disabled:opacity-50 disabled:cursor-not-allowed
                    transition-all duration-300 rounded-lg
                    hover:bg-primary/10"
                >
                  <Send className={`w-5 h-5 ${isPending ? 'animate-pulse' : ''}`} />
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      
      <div className="w-72 p-4 border-l border-base-300 dark:border-base-700">
        {isFilesVisible && (
          <FileListComponent visible={isFilesVisible} files={files} />
        )}
      </div>
    </div>
  );
}