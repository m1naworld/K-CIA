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
    <div className="flex items-end gap-3 border-t border-white/10 pt-3">
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="예: 카페 입지로 괜찮은 구역을 근거와 함께 추천해줘"
        className="intel-control max-h-28 min-h-[44px] flex-1 resize-none rounded-[1rem] border-0 bg-transparent px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/20"
        disabled={isStreaming}
        rows={1}
      />
      {isStreaming ? (
        <Button
          variant="ghost"
          size="icon"
          className="intel-text-danger h-11 w-11 shrink-0 rounded-[1rem] hover:bg-destructive/10 hover:text-destructive"
          onClick={cancel}
        >
          <Square className="h-4 w-4 fill-current" />
        </Button>
      ) : (
        <Button
          size="icon"
          className="intel-button-primary h-11 w-11 shrink-0 rounded-[1rem]"
          onClick={handleSubmit}
          disabled={!input.trim()}
        >
          <Send className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
