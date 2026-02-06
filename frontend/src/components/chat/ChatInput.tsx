"use client";

import { useState, useCallback, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Send, Square } from "lucide-react";
import { useStreamingChat } from "@/hooks/useStreamingChat";

export function ChatInput() {
  const [input, setInput] = useState("");
  const { sendMessage, cancel, isStreaming } = useStreamingChat();

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    sendMessage(trimmed);
    setInput("");
  }, [input, isStreaming, sendMessage]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  return (
    <div className="flex items-end gap-2 border-t border-white/10 pt-3">
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="질문을 입력하세요..."
        className="max-h-24 min-h-[40px] flex-1 resize-none rounded-lg bg-gray-800 px-3 py-2 text-sm text-white placeholder-white/40 focus:outline-none focus:ring-1 focus:ring-blue-500"
        disabled={isStreaming}
        rows={1}
      />
      {isStreaming ? (
        <Button
          variant="ghost"
          size="icon"
          className="h-10 w-10 shrink-0 text-red-400 hover:bg-red-500/10 hover:text-red-300"
          onClick={cancel}
        >
          <Square className="h-4 w-4 fill-current" />
        </Button>
      ) : (
        <Button
          variant="ghost"
          size="icon"
          className="h-10 w-10 shrink-0 text-blue-400 hover:bg-blue-500/10 hover:text-blue-300"
          onClick={handleSubmit}
          disabled={!input.trim()}
        >
          <Send className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
