import { create } from "zustand";
import type {
  ChatMessage,
  ChatRoute,
  SqlEvent,
  InsightEvent,
  AppliedCategoryInfo,
} from "@/types/chat";

interface ChatState {
  isOpen: boolean;
  isExpanded: boolean;
  messages: ChatMessage[];
  isStreaming: boolean;

  toggleOpen: () => void;
  toggleExpanded: () => void;
  addUserMessage: (content: string) => string;
  startAssistantMessage: () => string;
  updateAssistantRoute: (id: string, route: ChatRoute) => void;
  updateAssistantSql: (id: string, sql: SqlEvent) => void;
  updateAssistantInsight: (id: string, insight: InsightEvent) => void;
  setAssistantCategoryInfo: (id: string, info: AppliedCategoryInfo) => void;
  completeAssistantMessage: (id: string, dataAsof: string) => void;
  setAssistantError: (id: string, error: string) => void;
  clearMessages: () => void;
  setStreaming: (streaming: boolean) => void;
}

function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

export const useChatStore = create<ChatState>((set) => ({
  isOpen: false,
  isExpanded: false,
  messages: [],
  isStreaming: false,

  toggleOpen: () =>
    set((state) => ({
      isOpen: !state.isOpen,
    })),

  toggleExpanded: () =>
    set((state) => ({
      isExpanded: !state.isExpanded,
    })),

  addUserMessage: (content: string) => {
    const id = generateId();
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role: "user",
          content,
          timestamp: new Date(),
        },
      ],
    }));
    return id;
  },

  startAssistantMessage: () => {
    const id = generateId();
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id,
          role: "assistant",
          content: "",
          timestamp: new Date(),
          isStreaming: true,
        },
      ],
      isStreaming: true,
    }));
    return id;
  },

  updateAssistantRoute: (id: string, route: ChatRoute) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, route } : msg
      ),
    })),

  updateAssistantSql: (id: string, sql: SqlEvent) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, sql } : msg
      ),
    })),

  updateAssistantInsight: (id: string, insight: InsightEvent) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id
          ? { ...msg, insight, content: insight.summary || msg.content }
          : msg
      ),
    })),

  setAssistantCategoryInfo: (id: string, info: AppliedCategoryInfo) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, categoryInfo: info } : msg
      ),
    })),

  completeAssistantMessage: (id: string, dataAsof: string) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, dataAsof, isStreaming: false } : msg
      ),
      isStreaming: false,
    })),

  setAssistantError: (id: string, error: string) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, error, isStreaming: false } : msg
      ),
      isStreaming: false,
    })),

  clearMessages: () => set({ messages: [] }),

  setStreaming: (streaming: boolean) => set({ isStreaming: streaming }),
}));
