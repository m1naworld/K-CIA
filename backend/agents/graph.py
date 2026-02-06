"""LangGraph state definition and graph builder for K-CIA agents."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from agents.insight_agent import insight_agent_node
from agents.sql_agent import sql_agent_node
from agents.supervisor import supervisor_node


class AgentState(TypedDict, total=False):
    """Shared state flowing through the agent graph."""

    question: str
    messages: list[dict]  # Conversation history: [{"role": "user"|"assistant", "content": "..."}]
    route: str  # "sql" | "insight" | "both"
    sql_text: str | None
    sql_result: Any
    insight: dict | None
    data_asof: str | None
    selected_hex_detail: dict | None


def _route_after_supervisor(state: AgentState) -> str:
    """Conditional edge: pick next node based on supervisor route."""
    route = state.get("route", "insight")
    if route == "sql":
        return "sql_agent"
    if route == "both":
        return "sql_agent"
    return "insight_agent"


def _route_after_sql(state: AgentState) -> str:
    """After SQL agent: go to END or insight_agent depending on route."""
    if state.get("route") == "both":
        return "insight_agent"
    return END


def build_graph() -> Any:
    """Build and compile the K-CIA agent graph."""
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("sql_agent", sql_agent_node)
    graph.add_node("insight_agent", insight_agent_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {"sql_agent": "sql_agent", "insight_agent": "insight_agent"},
    )
    graph.add_conditional_edges(
        "sql_agent",
        _route_after_sql,
        {"insight_agent": "insight_agent", END: END},
    )
    graph.add_edge("insight_agent", END)

    return graph.compile()
