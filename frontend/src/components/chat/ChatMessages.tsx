"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatStore } from "@/store/chatStore";
import { ChatMessage } from "./ChatMessage";

export function ChatMessages() {
  const messages = useChatStore((state) => state.messages);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-center text-sm text-slate-500 dark:text-white/40">
        <p>성수동 상권에 대해 질문해보세요.</p>
        <p className="mt-1 text-xs">예: &quot;카페 매출 Top3 추천해줘&quot;</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full pr-4" ref={scrollRef}>
      <div className="flex flex-col gap-4 pb-2">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
      </div>
    </ScrollArea>
  );
}
