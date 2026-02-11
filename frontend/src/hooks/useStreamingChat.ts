"use client";

import { useCallback, useRef } from "react";
import { useChatStore } from "@/store/chatStore";
import { useMapStore } from "@/store/mapStore";
import { trackEvent } from "@/lib/analytics";
import type {
  ChatRequest,
  ChatMessagePayload,
  RoutingEvent,
  SqlEvent,
  InsightEvent,
  DoneEvent,
  ErrorEvent,
} from "@/types/chat";

interface UseStreamingChatReturn {
  sendMessage: (question: string) => Promise<void>;
  cancel: () => void;
  isStreaming: boolean;
}

export function useStreamingChat(): UseStreamingChatReturn {
  const abortControllerRef = useRef<AbortController | null>(null);

  const {
    messages,
    isStreaming,
    addUserMessage,
    startAssistantMessage,
    updateAssistantRoute,
    updateAssistantSql,
    updateAssistantInsight,
    completeAssistantMessage,
    setAssistantError,
    setStreaming,
  } = useChatStore();

  const { category, quarter, hexDetail } = useMapStore();

  const handleEvent = useCallback(
    (
      assistantId: string,
      eventType: string,
      data: RoutingEvent | SqlEvent | InsightEvent | DoneEvent | ErrorEvent
    ) => {
      switch (eventType) {
        case "routing":
          updateAssistantRoute(
            assistantId,
            (data as RoutingEvent).route
          );
          break;
        case "sql":
          updateAssistantSql(assistantId, data as SqlEvent);
          break;
        case "insight":
          updateAssistantInsight(assistantId, data as InsightEvent);
          break;
        case "done":
          completeAssistantMessage(
            assistantId,
            (data as DoneEvent).data_asof
          );
          break;
        case "error":
          setAssistantError(assistantId, (data as ErrorEvent).message);
          break;
        default:
          console.warn("Unknown SSE event:", eventType);
      }
    },
    [
      updateAssistantRoute,
      updateAssistantSql,
      updateAssistantInsight,
      completeAssistantMessage,
      setAssistantError,
    ]
  );

  const sendMessage = useCallback(
    async (question: string) => {
      if (isStreaming) return;

      // Add user message
      addUserMessage(question);

      trackEvent("ASK", {
        area_type: "COMMERCIAL_AREA",
        category,
        qtr: quarter,
        question_len: question.length,
      });

      // Start assistant message
      const assistantId = startAssistantMessage();

      const historyMessages: ChatMessagePayload[] = messages
        .filter((m) => m.role === "user" || m.role === "assistant")
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      const payload: ChatRequest = {
        question,
        messages: historyMessages,
        area_type: "COMMERCIAL_AREA",
      };
      if (category && category !== "all") {
        payload.category = category;
      }
      if (quarter && quarter !== "latest") {
        payload.qtr = quarter;
      }
      if (hexDetail) {
        payload.selected_hex_detail = hexDetail;
      }

      // Create abort controller
      abortControllerRef.current = new AbortController();

      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

      try {
        const response = await fetch(`${apiUrl}/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify(payload),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let currentEvent = "";
          let currentData = "";

          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              currentData = line.slice(5).trim();
            } else if (line === "" && currentEvent && currentData) {
              // Empty line signals end of event
              try {
                const data = JSON.parse(currentData);
                handleEvent(assistantId, currentEvent, data);
              } catch (e) {
                console.error("Failed to parse SSE data:", e);
              }
              currentEvent = "";
              currentData = "";
            }
          }
        }
      } catch (error) {
        if (error instanceof Error) {
          if (error.name === "AbortError") {
            setAssistantError(assistantId, "요청이 취소되었습니다.");
          } else {
            setAssistantError(
              assistantId,
              error.message || "알 수 없는 오류가 발생했습니다."
            );
          }
        }
      } finally {
        abortControllerRef.current = null;
        setStreaming(false);
      }
    },
    [
      isStreaming,
      messages,
      category,
      quarter,
      addUserMessage,
      startAssistantMessage,
      setAssistantError,
      setStreaming,
      handleEvent,
    ]
  );

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  return {
    sendMessage,
    cancel,
    isStreaming,
  };
}
