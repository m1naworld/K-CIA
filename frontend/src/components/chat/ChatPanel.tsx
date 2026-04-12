"use client";

import { Button } from "@/components/ui/button";
import { MessageSquare, X, Maximize2, Minimize2, Trash2 } from "lucide-react";
import { useChatStore } from "@/store/chatStore";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";
import { useMapStore } from "@/store/mapStore";

export default function ChatPanel() {
  const { isOpen, isExpanded, toggleOpen, toggleExpanded, clearMessages, messages } =
    useChatStore();
  const { sidebarOpen } = useMapStore();

  if (!isOpen) {
    return (
      <Button
        onClick={toggleOpen}
        className={`intel-fab fixed bottom-4 z-50 h-16 w-16 rounded-[1.4rem] border border-border/60 transition-all duration-300 hover:scale-[1.02] hover:brightness-105 ${
          sidebarOpen ? "right-4 md:right-[22.5rem] 2xl:right-[24.5rem]" : "right-4 md:right-6"
        }`}
        size="icon"
      >
        <MessageSquare className="h-6 w-6" />
      </Button>
    );
  }

  const panelWidth = isExpanded
    ? "w-[min(560px,calc(100vw-1.5rem))]"
    : "w-[min(440px,calc(100vw-1.5rem))]";
  const panelHeight = isExpanded
    ? "h-[min(680px,calc(100vh-3rem))]"
    : "h-[min(560px,calc(100vh-3rem))]";

  return (
    <div
      className={`intel-panel fixed bottom-4 z-50 flex flex-col rounded-[1.75rem] text-foreground transition-all duration-300 ${panelWidth} ${panelHeight} ${
        sidebarOpen ? "right-4 md:right-[22.5rem] 2xl:right-[24.5rem]" : "right-4 md:right-6"
      }`}
    >
      <div className="flex items-start justify-between border-b border-border/60 px-5 py-4">
        <div>
          <div className="intel-kicker">AI Consultant Overlay</div>
          <h3 className="mt-2 flex items-center gap-2 text-sm font-medium text-foreground">
            <MessageSquare className="intel-text-primary h-4 w-4" />
            K-CIA 상권 컨설턴트
          </h3>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            지도에서 보고 있는 구역 맥락을 이어받아 추천, 리스크, 실행 항목을 정리합니다.
          </p>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:bg-accent/60 hover:text-foreground"
              onClick={clearMessages}
              title="대화 초기화"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:bg-accent/60 hover:text-foreground"
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
            className="h-8 w-8 text-muted-foreground hover:bg-accent/60 hover:text-foreground"
            onClick={toggleOpen}
            title="닫기"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden px-4 py-4">
        <div className="intel-panel-soft flex h-full flex-col rounded-[1.4rem] px-4 py-3">
          <ChatMessages />
        </div>
      </div>

      <div className="px-4 pb-4">
        <div className="intel-panel-soft rounded-[1.4rem] px-4 py-3">
          <ChatInput />
        </div>
      </div>
    </div>
  );
}
