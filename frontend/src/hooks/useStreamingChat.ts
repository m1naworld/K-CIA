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
    setAssistantCategoryInfo,
    completeAssistantMessage,
    setAssistantError,
    setStreaming,
  } = useChatStore();

  const { category, quarter, hexDetail, selectedHex, categories, setCategory } =
    useMapStore();

  const inferCategory = useCallback(
    (question: string) => {
      if (!categories.length) return null;
      const q = question.toLowerCase();
      const keywordMap: Array<{ keywords: string[]; serviceName: string }> = [
        {
          keywords: ["디저트", "디저트카페", "베이커리", "베이커리카페"],
          serviceName: "제과점",
        },
        {
          keywords: [
            "카페",
            "카페거리",
            "커피",
            "커피전문점",
            "커피 전문점",
            "커피숍",
            "커피샵",
            "브런치",
          ],
          serviceName: "커피-음료",
        },
        { keywords: ["치킨", "치킨집"], serviceName: "치킨전문점" },
        { keywords: ["호프", "맥주", "주점", "술집"], serviceName: "호프-간이주점" },
        { keywords: ["분식", "떡볶이"], serviceName: "분식전문점" },
        { keywords: ["한식", "한식당"], serviceName: "한식음식점" },
        { keywords: ["중식", "중국집"], serviceName: "중식음식점" },
        { keywords: ["일식", "초밥"], serviceName: "일식음식점" },
        { keywords: ["양식"], serviceName: "양식음식점" },
        { keywords: ["패스트푸드", "햄버거"], serviceName: "패스트푸드점" },
        { keywords: ["편의점"], serviceName: "편의점" },
        { keywords: ["미용실", "헤어샵"], serviceName: "미용실" },
        { keywords: ["네일", "네일샵"], serviceName: "네일숍" },
        { keywords: ["pc방", "피씨방"], serviceName: "PC방" },
      ];

      const matched = keywordMap.find((entry) =>
        entry.keywords.some((keyword) => q.includes(keyword))
      );
      if (!matched) return null;

      const categoryMatch = categories.find(
        (cat) => cat.service_name === matched.serviceName
      );
      if (!categoryMatch) return null;
      return {
        service_code: categoryMatch.service_code,
        service_name: categoryMatch.service_name,
      };
    },
    [categories]
  );

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

      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const inferredCategory = selectedHex ? inferCategory(question) : null;

      let selectedHexDetail =
        hexDetail && selectedHex && hexDetail.h3_index === selectedHex
          ? hexDetail
          : null;

      if (selectedHex && !selectedHexDetail) {
        const params = new URLSearchParams();
        params.set("area_type", "COMMERCIAL_AREA");
        if (quarter && quarter !== "latest") {
          params.set("qtr", quarter);
        }
        if (category && category !== "all") {
          params.set("category", category);
        }
        try {
          const res = await fetch(
            `${apiUrl}/api/map/hexagon/${selectedHex}?${params.toString()}`
          );
          if (res.ok) {
            selectedHexDetail = await res.json();
          }
        } catch {}
      }

      if (inferredCategory && selectedHex) {
        const params = new URLSearchParams();
        params.set("area_type", "COMMERCIAL_AREA");
        if (quarter && quarter !== "latest") {
          params.set("qtr", quarter);
        }
        params.set("category", inferredCategory.service_code);
        try {
          const res = await fetch(
            `${apiUrl}/api/map/hexagon/${selectedHex}?${params.toString()}`
          );
          if (res.ok) {
            selectedHexDetail = await res.json();
          }
        } catch {}
      }

      const payload: ChatRequest = {
        question,
        messages: historyMessages,
        area_type: "COMMERCIAL_AREA",
      };
      if (inferredCategory) {
        payload.category = inferredCategory.service_code;
      } else if (category && category !== "all") {
        payload.category = category;
      }
      if (quarter && quarter !== "latest") {
        payload.qtr = quarter;
      }
      if (selectedHexDetail) {
        payload.selected_hex_detail = selectedHexDetail;
      }

      if (inferredCategory) {
        setAssistantCategoryInfo(assistantId, {
          service_code: inferredCategory.service_code,
          service_name: inferredCategory.service_name,
          source: "inferred",
        });
        if (category !== inferredCategory.service_code) {
          setCategory(inferredCategory.service_code);
        }
      }

      // Create abort controller
      abortControllerRef.current = new AbortController();

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
      hexDetail,
      selectedHex,
      setCategory,
      addUserMessage,
      startAssistantMessage,
      setAssistantCategoryInfo,
      setAssistantError,
      setStreaming,
      handleEvent,
      inferCategory,
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
