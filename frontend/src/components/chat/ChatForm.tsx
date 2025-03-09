import { FormEvent, useState } from 'react';
import { Settings, Send, ChevronUp, ChevronDown } from 'lucide-react';
import { NotificationBanner } from '@/components/ui/notification-banner';
import { useMessageLimits } from '@/hooks/useMessageLimits';

interface ChatFormProps {
  question: string;
  setQuestion: (value: string) => void;
  system_prompt: string;
  setPrompt: (value: string) => void;
  ast_bool: boolean;
  setAst: (value: boolean) => void;
  forceReindex: boolean;
  setForceReindex: (value: boolean) => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  isPending: boolean;
}

export default function ChatForm({
  question,
  setQuestion,
  system_prompt,
  setPrompt,
  ast_bool,
  setAst,
  forceReindex,
  setForceReindex,
  onSubmit,
  isPending
}: ChatFormProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const { messagesLeft, shouldShowNotification, refreshLimits } = useMessageLimits();

  const handleResetPrompt = () => {
    setPrompt("You are a coding assistant. Please answer the user's coding questions step by step, considering the code content and file structure. If unsure, say 'I don't know.'");
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    await onSubmit(e);
    // Refresh limits after submission
    refreshLimits();
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm border-t border-slate-200 dark:border-slate-800 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Notification Banner */}
        <NotificationBanner
          messagesLeft={messagesLeft}
          isVisible={shouldShowNotification}
        />

        <form onSubmit={handleSubmit} className="relative">
          <div className={`
            absolute bottom-full left-0 right-0 mb-2
            bg-white dark:bg-slate-900 
            rounded-lg shadow-lg
            border border-slate-200 dark:border-slate-700
            transition-all duration-200 ease-in-out
            ${isSettingsOpen ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'}
          `}>
            <div className="p-4 space-y-4">
              <div className="space-y-2">
                <textarea
                  placeholder="System Prompt"
                  value={system_prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="w-full min-h-[100px] p-3 rounded-lg
                    border border-slate-200 dark:border-slate-700
                    bg-white dark:bg-slate-800
                    focus:ring-2 focus:ring-blue-500 focus:border-transparent
                    resize-none"
                />
              </div>

              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={handleResetPrompt}
                  className="px-3 py-1.5 text-sm font-medium
                    text-blue-600 bg-blue-50 rounded-md
                    hover:bg-blue-100 transition-colors
                    dark:bg-blue-900/30 dark:text-blue-400
                    dark:hover:bg-blue-900/50"
                >
                  Reset to Default Prompt
                </button>

                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={ast_bool}
                      onChange={() => setAst(!ast_bool)}
                      className="w-4 h-4 rounded border-slate-300
                        text-blue-600 focus:ring-blue-500
                        dark:border-slate-600"
                    />
                    <span className="text-sm text-slate-700 dark:text-slate-300">
                      Include AST
                    </span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={forceReindex}
                      onChange={() => setForceReindex(!forceReindex)}
                      className="w-4 h-4 rounded border-slate-300
                        text-blue-600 focus:ring-blue-500
                        dark:border-slate-600"
                    />
                    <span className="text-sm text-slate-700 dark:text-slate-300">
                      Force Reindex
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <div className="relative flex items-center bg-white dark:bg-slate-900 rounded-lg shadow-sm">
            <button
              type="button"
              onClick={() => setIsSettingsOpen(!isSettingsOpen)}
              className="absolute left-4 p-1 text-slate-400 
                hover:text-slate-600 dark:hover:text-slate-300 
                transition-colors rounded-md
                hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <Settings className="w-5 h-5" />
              {isSettingsOpen ? (
                <ChevronDown className="w-4 h-4 absolute -right-5 top-1" />
              ) : (
                <ChevronUp className="w-4 h-4 absolute -right-5 top-1" />
              )}
            </button>

            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Enter your question about the code..."
              className="w-full pl-16 pr-16 py-3 rounded-lg
                border border-slate-200 dark:border-slate-700
                bg-white dark:bg-slate-900
                focus:ring-2 focus:ring-blue-500 focus:border-transparent
                placeholder-slate-400"
              required
            />

            <button
              type="submit"
              disabled={isPending}
              className="absolute right-4 p-1.5 text-blue-600 
                hover:text-blue-700 dark:text-blue-500 
                dark:hover:text-blue-400 disabled:opacity-50 
                disabled:cursor-not-allowed transition-colors
                hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-md"
            >
              <Send className={`w-5 h-5 ${isPending ? 'animate-pulse' : ''}`} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}