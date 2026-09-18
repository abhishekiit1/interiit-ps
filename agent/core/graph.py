from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage
from langgraph.prebuilt.tool_node import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import load_prompt
from state import InvestigationState
import yaml

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodes.k8s_tool_node import k8s_tool_function
from nodes.git_tool_node import git_tool_function
from nodes.loki_tool_node import loki_tool_function
from nodes.prometheus_tool_node import prometheus_tool_function

# importing nodes
from nodes.supervisor_node import (supervisor_function, initial_investigation, iterative_investigation)
from nodes.summmary_eval_node import (summary_eval_function)
from nodes.tool_proxy_node import (tool_proxy)



def supervisor_routing(state: InvestigationState) -> str:
    next_step = state.get("next_node", 0)
    if next_step == 0:
        return "summary"
    else:
        return "tool"


def tool_routing(state: InvestigationState) -> int:
    next_node = state.get("next_node", 0)
    # Pick the lowest set bit to run first.
    if next_node & 1:
        return 1
    if next_node & 2:
        return 2
    if next_node & 4:
        return 4
    if next_node & 8:
        return 8
    return 0


def post_tool_routing(state: InvestigationState) -> str:
    """After a tool runs, check if there are remaining tools to execute.
    If the next_node still has bits set (after the tool node cleared its own bit),
    route back to ToolProxyNode; otherwise route to SupervisorNode."""
    remaining = state.get("next_node", 0)
    if remaining > 0:
        print(f"  🔄 More tools pending (next_node={remaining}), routing to ToolProxy")
        return "tool_proxy"
    else:
        print(f"  ↩️ All tools done, routing back to Supervisor")
        return "supervisor"


# Wrapper functions for tool nodes that clear their bit from next_node after execution
def prometheus_wrapper(state: InvestigationState) -> InvestigationState:
    print(f"\n  🔧 [PrometheusToolNode] ENTER (next_node={state.get('next_node', 0)})")
    state = prometheus_tool_function(state)
    # Clear bit 1 (Prometheus)
    state["next_node"] = state.get("next_node", 0) & ~1
    print(f"  🔧 [PrometheusToolNode] EXIT (next_node={state.get('next_node', 0)}, evidence_count={len(state.get('evidence', []))})")
    return state


def loki_wrapper(state: InvestigationState) -> InvestigationState:
    print(f"\n  🔧 [LokiToolNode] ENTER (next_node={state.get('next_node', 0)})")
    state = loki_tool_function(state)
    # Clear bit 2 (Loki)
    state["next_node"] = state.get("next_node", 0) & ~2
    print(f"  🔧 [LokiToolNode] EXIT (next_node={state.get('next_node', 0)}, evidence_count={len(state.get('evidence', []))})")
    return state


def k8s_wrapper(state: InvestigationState) -> InvestigationState:
    print(f"\n  🔧 [K8sToolNode] ENTER (next_node={state.get('next_node', 0)})")
    state = k8s_tool_function(state)
    # Clear bit 4 (K8s)
    state["next_node"] = state.get("next_node", 0) & ~4
    print(f"  🔧 [K8sToolNode] EXIT (next_node={state.get('next_node', 0)}, evidence_count={len(state.get('evidence', []))})")
    return state


def git_wrapper(state: InvestigationState) -> InvestigationState:
    print(f"\n  🔧 [GitToolNode] ENTER (next_node={state.get('next_node', 0)})")
    state = git_tool_function(state)
    # Clear bit 8 (Git)
    state["next_node"] = state.get("next_node", 0) & ~8
    print(f"  🔧 [GitToolNode] EXIT (next_node={state.get('next_node', 0)}, evidence_count={len(state.get('evidence', []))})")
    return state


# initializing graph
graph = StateGraph(InvestigationState)
# initializing nodes
graph.add_node("SupervisorNode",supervisor_function)
graph.add_node("PrometheusToolNode",prometheus_wrapper)
graph.add_node("LokiToolNode",loki_wrapper)
graph.add_node("K8sToolNode",k8s_wrapper)
graph.add_node("GitToolNode",git_wrapper)
graph.add_node("ToolProxyNode",tool_proxy)
graph.add_node("SummaryEvalNode",summary_eval_function)
graph.add_conditional_edges(
    "SupervisorNode",
    supervisor_routing,
    {
        "summary":"SummaryEvalNode",
        "tool":"ToolProxyNode"
    }
)
graph.add_conditional_edges(
    "ToolProxyNode",
    tool_routing,
    {
        1:"PrometheusToolNode",
        2:"LokiToolNode",
        4:"K8sToolNode",
        8:"GitToolNode",
        0:"SummaryEvalNode"
    }
)

# After each tool node, check if more tools need to run (multi-tool bitmask support)
for tool_node in ["PrometheusToolNode", "LokiToolNode", "K8sToolNode", "GitToolNode"]:
    graph.add_conditional_edges(
        tool_node,
        post_tool_routing,
        {
            "tool_proxy": "ToolProxyNode",
            "supervisor": "SupervisorNode",
        }
    )

graph.add_edge(START,"SupervisorNode")
graph.add_edge("SummaryEvalNode", END)

agent_graph = graph.compile()

try:
    with open("../graph_diagram.png","wb") as fd:
        fd.write(agent_graph.get_graph().draw_mermaid_png())
except Exception:
    pass  # Don't crash if diagram generation fails
