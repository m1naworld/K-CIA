"use client";

import { Button } from "@/components/ui/button";
import { MessageSquare, X, Maximize2, Minimize2, Trash2 } from "lucide-react";
import { useChatStore } from "@/store/chatStore";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";

export default function ChatPanel() {
  const { isOpen, isExpanded, toggleOpen, toggleExpanded, clearMessages, messages } =
    useChatStore();

  // Floating button when closed
  if (!isOpen) {
    return (
      <Button
        onClick={toggleOpen}
        className="fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full bg-blue-600 shadow-lg hover:bg-blue-500"
        size="icon"
      >
        <MessageSquare className="h-6 w-6" />
      </Button>
    );
  }

  // Panel dimensions
  const panelWidth = isExpanded ? "w-[500px]" : "w-[400px]";
  const panelHeight = isExpanded ? "h-[600px]" : "h-[500px]";

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 ${panelWidth} ${panelHeight} flex flex-col rounded-xl border border-white/10 bg-gray-950 shadow-2xl`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <h3 className="flex items-center gap-2 text-sm font-medium text-white">
          <MessageSquare className="h-4 w-4 text-blue-400" />
          AI 상권 컨설턴트
        </h3>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-white/50 hover:bg-white/10 hover:text-white"
              onClick={clearMessages}
              title="대화 초기화"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-white/50 hover:bg-white/10 hover:text-white"
            onClick={toggleExpanded}
            title={isExpanded ? "축소" : "확장"}
          >
            {isExpanded ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-white/50 hover:bg-white/10 hover:text-white"
            onClick={toggleOpen}
            title="닫기"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-hidden px-4 py-3">
        <ChatMessages />
      </div>

      {/* Input area */}
      <div className="px-4 pb-4">
        <ChatInput />
      </div>
    </div>
  );
}
