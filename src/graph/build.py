"""
LangGraph Builder
================

Xây dựng LangGraph workflow cho email processing pipeline.

Workflow:
START -> triage -> agent -> sensitive -> END

Architecture:
- StateGraph với EmailState
- Linear flow qua 3 processing nodes
- Compile thành executable graph
"""

from langgraph.graph import StateGraph, START, END
from .state import EmailState
from .nodes import node_triage, node_agent, node_sensitive

def build_graph():
    """
    Xây dựng LangGraph workflow cho email processing
    
    Workflow:
    1. triage: Phân loại email và xác định priority
    2. agent: Generate draft reply nếu cần
    3. sensitive: Handle HITL approval cho sensitive actions
    
    Returns:
        Compiled LangGraph ready để execute
    """
    g = StateGraph(EmailState)
    
    # Add processing nodes
    g.add_node("triage", node_triage)
    g.add_node("agent", node_agent)
    g.add_node("sensitive", node_sensitive)
    
    # Define linear flow
    g.add_edge(START, "triage")
    g.add_edge("triage", "agent")
    g.add_edge("agent", "sensitive")
    g.add_edge("sensitive", END)
    
    return g.compile()
