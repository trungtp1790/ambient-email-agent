from langgraph.graph import StateGraph, START, END
from .state import EmailState
from .nodes import node_triage, node_agent, node_sensitive

def build_graph():
    g = StateGraph(EmailState)
    g.add_node("triage", node_triage)
    g.add_node("agent", node_agent)
    g.add_node("sensitive", node_sensitive)
    g.add_edge(START, "triage")
    g.add_edge("triage", "agent")
    g.add_edge("agent", "sensitive")
    g.add_edge("sensitive", END)
    return g.compile()
