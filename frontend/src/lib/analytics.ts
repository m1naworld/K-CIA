type EventPayload = {
  eventType: string;
  sessionId: string | null;
  userId?: string | null;
  props?: Record<string, unknown>;
};

const SESSION_KEY = "kcia_session_id";

function getSessionId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const existing = window.localStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    const newId = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    window.localStorage.setItem(SESSION_KEY, newId);
    return newId;
  } catch {
    return null;
  }
}

export async function trackEvent(
  eventType: string,
  props: Record<string, unknown> = {},
  userId?: string | null
): Promise<void> {
  if (typeof window === "undefined") return;
  const sessionId = getSessionId();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const payload: EventPayload = {
    eventType,
    sessionId,
    userId,
    props,
  };

  try {
    await fetch(`${apiUrl}/api/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        events: [
          {
            event_type: payload.eventType,
            session_id: payload.sessionId,
            user_id: payload.userId ?? null,
            props: payload.props ?? {},
          },
        ],
      }),
    });
  } catch {
    // Non-blocking
  }
}
