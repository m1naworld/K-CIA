"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatStore } from "@/store/chatStore";
import { ChatMessage } from "./ChatMessage";

export function ChatMessages() {
  const messages = useChatStore((state) => state.messages);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-center text-sm text-muted-foreground">
        <div className="intel-kicker">Evidence-led prompts</div>
        <p className="mt-3 text-sm font-medium text-foreground">
          지금 보고 있는 상권을 기준으로 질문해보세요.
        </p>
        <p className="mt-2 text-xs leading-6 text-muted-foreground">
          예: &quot;카페 매출이 높은 구역 3곳을 리스크와 함께 추천해줘&quot;
        </p>
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
