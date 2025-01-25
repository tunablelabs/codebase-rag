interface Message {
    type: 'user' | 'bot';
    text: string;
  }
  
  interface ChatWindowProps {
    messages: Message[];
    isPending: boolean;
  }
  
  export default function ChatWindow({ messages, isPending }: ChatWindowProps) {
    return (
      <div className="min-h-[360px] grow max-h-[320px] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-500 scrollbar-track-gray-200 dark:scrollbar-thumb-gray-700 dark:scrollbar-track-gray-900 rounded-xl bg-white/70 p-6 shadow-lg backdrop-blur-sm dark:bg-slate-900/70">
        {messages.length > 0 ? (
          <div className="space-y-2">
            {messages.map((msg, index) => (
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
        {isPending && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-800 p-3 rounded-lg">
              Processing...
            </div>
          </div>
        )}
      </div>
    );
  }