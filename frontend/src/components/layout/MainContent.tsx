import { FormEvent, useEffect, useRef, useState } from "react";

import CodeBlock  from './CodeBlock';
import { FileListComponent } from "../file/FileList";
import ShowStats from "../file/ShowStats";
import { ChatOptions, Session } from "@/types";
import { 
  Settings, 
  Send, 
  ChevronUp, 
  ChevronDown, 
  Loader2, 
  MessageSquare, 
  Bot, 
  User, 
  BarChart2, 
  RefreshCw, 
  File,
  ArrowDown
} from 'lucide-react';
import ReactMarkdown from "react-markdown"
interface Stats {
  total_code_files: number;
  language_distribution: {
    [language: string]: string;
  };
}

interface MainContentProps {
  currentSession: Session | null;
  isFilesVisible: boolean;
  isStatsVisible: boolean;
  stats?: Stats | null;
  files: string[];
  isPending: boolean;
  chatOptions: ChatOptions;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  onPromptChange: (prompt: string) => void;
  onResetPrompt: () => void;
  onAstChange: () => void;
  onForceReindexChange: () => void;
  onLlmEvaluator: () => void;
}
interface ContentBlock {
  type: 'text' | 'code';
  content: string;
  language?: string;
}
function MainContent({
  currentSession,
  isFilesVisible,
  isStatsVisible,
  stats,
  files,
  isPending,
  chatOptions,
  onSubmit,
  onPromptChange,
  onResetPrompt,
  onAstChange,
  onForceReindexChange,
  onLlmEvaluator,
}: MainContentProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isMetricsExpanded, setIsMetricsExpanded] = useState<{[key: string]: boolean}>({});
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const suggestedQuestions = [
    "How does this function work?",
    "Can you summarize this file?",
    "What are the key dependencies?",
    "Are there any security risks?",
  ];

  useEffect(() => {
    if (currentSession?.messages) {
      const newExpanded = {...isMetricsExpanded};
      currentSession.messages.forEach((_, index) => {
        if (!(index in newExpanded)) {
          newExpanded[index] = true;
        }
      });
      setIsMetricsExpanded(newExpanded);
    }
  }, [currentSession?.messages]);

  useEffect(() => {
    const scrollToBottom = () => {
      if (chatContainerRef.current) {
        const scrollHeight = chatContainerRef.current.scrollHeight;
        chatContainerRef.current.scrollTo({
          top: scrollHeight,
          behavior: 'smooth'
        });
      }
    };

    scrollToBottom();
    const timeoutId = setTimeout(scrollToBottom, 100);
    return () => clearTimeout(timeoutId);
  }, [currentSession?.messages, isPending]);

  useEffect(() => {
    const handleScroll = () => {
      if (chatContainerRef.current) {
        const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
        const isNotAtBottom = scrollHeight - scrollTop - clientHeight > 100;
        setShowScrollButton(isNotAtBottom);
      }
    };

    const chatContainer = chatContainerRef.current;
    if (chatContainer) {
      chatContainer.addEventListener('scroll', handleScroll);
      return () => chatContainer.removeEventListener('scroll', handleScroll);
    }
  }, []);

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  const renderSourceFiles = (sourceFiles: string) => {
    const files = sourceFiles.split(',').map(file => file.trim());
    return (
      <div className="mt-2 bg-base-200/40 dark:bg-base-300/30 rounded-lg p-2.5">
        <div className="flex items-center gap-2 text-xs text-base-content/60 mb-2">
          <File className="w-3.5 h-3.5" />
          <span className="font-medium">Source Files:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {files.map((file, index) => (
            <div 
              key={index}
              className="bg-base-100/50 dark:bg-base-200/40 px-2.5 py-1.5 rounded-md
                text-xs text-base-content/70 font-mono"
            >
              {file}
            </div>
          ))}
        </div>
      </div>
    );
  };
  const detectCodeBlocks = (text: string): ContentBlock[] => {
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    const blocks: ContentBlock[] = [];
    let lastIndex = 0;
    let match;
  
    while ((match = codeBlockRegex.exec(text)) !== null) {
      // Add text before code block
      if (match.index > lastIndex) {
        blocks.push({
          type: 'text',
          content: text.slice(lastIndex, match.index)
        });
      }
  
      // Add code block
      blocks.push({
        type: 'code',
        language: match[1] || '',
        content: match[2].trim()
      });
  
      lastIndex = match.index + match[0].length;
    }
  
    // Add remaining text after last code block
    if (lastIndex < text.length) {
      blocks.push({
        type: 'text',
        content: text.slice(lastIndex)
      });
    }
  
    return blocks;
  };
  const renderMetrics = (metric: any, index: number) => {
    if (!metric) return null;

    return (
      <div className="mt-2 bg-base-200/40 dark:bg-base-300/30 rounded-lg p-3
        border border-sky-500/20 dark:border-sky-500/20">
        <button
          onClick={() => setIsMetricsExpanded(prev => ({...prev, [index]: !prev[index]}))}
          className="w-full flex items-center justify-between text-sm text-base-content/70 hover:text-base-content"
        >
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4" />
            <span style={{ fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' }}>
              Response Quality Metrics
            </span>
          </div>
          {isMetricsExpanded[index] ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        <div className={`
          grid grid-cols-2 gap-3 transition-all duration-300
          ${isMetricsExpanded[index] ? 'mt-3 opacity-100' : 'h-0 opacity-0 overflow-hidden'}
        `}>
          {Object.entries(metric).map(([key, value]: [string, any]) => (
            <div key={key} className="space-y-1.5">
              <div className="text-xs text-base-content/60">{key}</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-base-300 dark:bg-base-400 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-primary/80 transition-all duration-500 ease-out"
                    style={{ width: `${value?.score * 100 || 0}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-base-content/80 tabular-nums">
                  {value?.score?.toFixed(2) || "0.00"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };
  const renderMessageContent = (text: string) => {
    const blocks = detectCodeBlocks(text);
    
    return blocks.map((block, index) => {
      if (block.type === 'code') {
        return <CodeBlock key={index} code={block.content} language={block.language} />;
      }
      return (
        <pre key={index} style={{ 
          fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
          fontSize: '0.875rem',
          lineHeight: '1.5',
          whiteSpace: 'pre-wrap'
        }}>
          <ReactMarkdown>{block.content}</ReactMarkdown>
        </pre>
      );
    });
  };
  const renderMessageBubble = (msg: any, index: number) => {
    console.log(msg)
    const isUser = msg.type === "user";
    const sourceFilesMatch = msg.text.match(/Source files:(.*?)(?=\n|$)/i);
    const messageText = sourceFilesMatch 
      ? msg.text.replace(sourceFilesMatch[0], '').trim()
      : msg.text;
    
    return (
      <div 
        key={index}
        className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""} group animate-fadeIn`}
      >
        <div className={`
          flex-shrink-0 w-8 h-8 rounded-full 
          ${isUser ? "bg-primary/90" : "bg-neutral/90"}
          flex items-center justify-center
          shadow-sm
        `}>
          {isUser ? (
            <User className="w-4 h-4 text-primary-content" />
          ) : (
            <Bot className="w-4 h-4 text-neutral-content" />
          )}
        </div>

        <div className={`flex flex-col gap-2 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
          <div className={`
            px-4 py-3 rounded-lg shadow-sm
            ${isUser 
              ? "bg-primary/90 text-primary-content" 
              : "bg-base-100 dark:bg-base-200/90 text-base-content"
            }
          `}>
          {renderMessageContent(messageText)}
          </div>

          {sourceFilesMatch && renderSourceFiles(sourceFilesMatch[1])}
          {!isUser && msg.metric && renderMetrics(msg.metric, index)}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-1">
      <div className="flex-1 px-1  pb-1">
        <div className="max-w-4xl mx-auto space-y-1.5">
          <div className="relative h-[calc(100vh-180px)] rounded-lg bg-base-200/30 dark:bg-base-300/20 
            shadow-lg backdrop-blur-sm transition-all duration-300 
            border border-sky-500/30 dark:border-sky-500/20">
            <div 
              ref={chatContainerRef}
              className="h-full overflow-y-auto pr-2 
              scrollbar-thin scrollbar-track-base-200/30 
              scrollbar-thumb-sky-500/20 hover:scrollbar-thumb-sky-500/40 
              dark:scrollbar-track-base-300/20 
              dark:scrollbar-thumb-sky-500/20 dark:hover:scrollbar-thumb-sky-500/40
              transition-colors duration-300"
          >
              <div className="h-full p-4 space-y-6">
                {currentSession?.messages.length ? (
                  <div className="space-y-6">
                    {currentSession.messages.map((msg, index) => renderMessageBubble(msg, index))}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center space-y-4">
                      <div className="w-16 h-16 mx-auto rounded-full bg-primary/10 flex items-center justify-center">
                        <MessageSquare className="w-8 h-8 text-primary/80" />
                      </div>
                      <div style={{ fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' }}>
                        <h3 className="text-lg font-medium text-base-content/90">
                          Start a Conversation
                        </h3>
                        <p className="text-sm text-base-content/60 mt-1">
                          Ask me anything about your code repository
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {isPending && (
                  <div className="flex items-start gap-3 animate-fadeIn">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-neutral/90 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-neutral-content" />
                    </div>
                    <div className="bg-base-100/90 dark:bg-base-200/90 rounded-lg px-4 py-3 shadow-sm
                      flex items-center gap-3">
                      <Loader2 className="w-4 h-4 animate-spin text-primary/80" />
                      <span style={{ 
                        fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                        fontSize: '0.875rem'
                      }}>
                        Processing your request...
                      </span>
                    </div>
                  </div>
                )}
              </div>
              <div className="mb-2 flex flex-wrap gap-2">
            {/*{suggestedQuestions.map((question, index) => (
              <button
                key={index}
                //onClick={() => setMessage(question)}
                className="px-3 py-1 text-sm bg-sky-500/20 text-sky-700 
                          hover:bg-sky-500/30 rounded-lg transition-all"
              >
                {question}
              </button>
            ))}*/}
          </div>
            </div>

            {showScrollButton && (
              <button
              onClick={scrollToBottom}
              className="absolute bottom-4 right-4 p-2 
                bg-base-200/80 hover:bg-base-200/95
                dark:bg-base-300/80 dark:hover:bg-base-300/95
                text-sky-500/80 hover:text-sky-500
                rounded-lg shadow-sm
                transition-all duration-300
                border border-sky-500/30
                backdrop-blur-sm"
              aria-label="Scroll to bottom"
            >
              <ArrowDown className="w-4 h-4" />
            </button>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="relative">
         
            <form onSubmit={onSubmit} className="relative">
              <div className={`
                absolute bottom-full left-0 right-0 mb-2
                 bg-base-100/95 dark:bg-base-200/95
                 rounded-lg shadow-lg
                border border-sky-500/30 dark:border-sky-500/30
                transition-all duration-300 ease-in-out backdrop-blur-sm
                ${isSettingsOpen ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'}
              `}>
                <div className="p-4 space-y-4">
                  <textarea
                    value={chatOptions.systemPrompt}
                    onChange={(e) => onPromptChange(e.target.value)}
                    className="w-full min-h-[100px] p-3 rounded-lg
                      bg-base-200/50 dark:bg-base-300/50
                      border border-sky-500/30 dark:border-sky-500/30
                      text-base-content placeholder:text-base-content/50
                      focus:ring-2 focus:ring-primary/30 focus:border-transparent
                      resize-none transition-all duration-300"
                    style={{ 
                      fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                      fontSize: '0.875rem'
                    }}
                    placeholder="Configure system prompt..."
                  />

                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                     <button
                        type="button"
                        onClick={onResetPrompt}
                        className="px-4 py-2 text-sm text-primary hover:bg-primary/10
                          rounded-lg transition-all duration-300"
                        style={{ 
                          fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
                        }}
                      >
                        Reset to Default
                      </button>

                      <button
                        type="button"
                        onClick={onResetPrompt}
                        className="px-4 py-2 text-sm text-primary hover:bg-primary/10
                          rounded-lg transition-all duration-300
                          flex items-center gap-2"
                        style={{ 
                          fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
                        }}
                      >
                        <RefreshCw className="w-4 h-4" />
                        Force Reindex
                      </button>
                    </div>

                    <div className="flex items-center gap-6">
                      <label className="flex items-center gap-2 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={chatOptions.astFlag}
                          onChange={onAstChange}
                          className="checkbox checkbox-primary checkbox-sm"
                        />
                        <span className="text-sm text-base-content/70 group-hover:text-base-content transition-colors"
                          style={{ 
                            fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
                          }}
                        >
                          Include AST
                        </span>
                      </label>

                      <label className="flex items-center gap-2 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={chatOptions.llmEvaluator}
                          onChange={onLlmEvaluator}
                          className="checkbox checkbox-primary checkbox-sm"
                        />
                        <span className="text-sm text-base-content/70 group-hover:text-base-content transition-colors"
                          style={{ 
                            fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
                          }}
                        >
                          LLM Evaluator
                        </span>
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
                  aria-label="Toggle settings"
                >
                  <Settings className="w-5 h-5" />
                </button>

                <input
                  name="message"
                  placeholder="Ask me about your code..."
                  className="w-full pl-16 pr-16 py-4 rounded-lg
                    bg-base-100/95 dark:bg-base-200/95
                    border border-sky-500/30 dark:border-sky-500/30
                    text-base-content placeholder:text-base-content/50
                    focus:outline-none focus:ring-[0.8px] focus:ring-blue/30


                    transition-all duration-300"
                  style={{ 
                    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                    fontSize: '0.875rem'
                  }}
                  required
                  disabled={isPending}
                />

                <button
                  type="submit"
                  disabled={isPending}
                  className="absolute right-4 p-2
                    text-primary hover:text-primary-focus
                    disabled:opacity-50 disabled:cursor-not-allowed
                    transition-all duration-300 rounded-lg
                    hover:bg-primary/10"
                  aria-label="Send message"
                >
                  <Send className={`w-5 h-5 ${isPending ? 'animate-pulse' : ''}`} />
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      <div className="w-72 p-4 border-l border-base-300/50 dark:border-base-700/50">
        {isFilesVisible && (
          <FileListComponent visible={isFilesVisible} files={files} />
        )}
        {isStatsVisible && stats && <ShowStats stats={stats} />}
      </div>
    </div>
  );
}

export default MainContent;
