import React from "react";

interface ChatWindowProps {
  currentSession: { id: string; messages: { type: "user" | "bot"; text: string }[] } | undefined;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ currentSession }) => {
  return (
    <div className="min-h-[320px] grow max-h-[320px] overflow-y-auto rounded-xl bg-white/70 p-6 shadow-lg backdrop-blur-sm">
      {currentSession?.messages.length ? (
        currentSession.messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}>
            <pre className={`whitespace-pre-wrap p-3 rounded-lg ${msg.type === "user" ? "bg-blue-500 text-white" : "bg-gray-200 text-gray-800"}`}>
              {msg.text}
            </pre>
          </div>
        ))
      ) : (
        <div className="text-gray-400">Your response will appear here</div>
      )}
    </div>
  );
};

export default ChatWindow;
