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
    # If multiple bits are set (e.g. 3), pick the lowest set bit to run first.
    # The iterative loop will call the next tool in subsequent iterations.
    if next_node & 1:
        return 1
    if next_node & 2:
        return 2
    if next_node & 4:
        return 4
    if next_node & 8:
        return 8
    return 0


# initializing graph
graph = StateGraph(InvestigationState)
# initializing nodes
graph.add_node("SupervisorNode",supervisor_function)
graph.add_node("PrometheusToolNode",prometheus_tool_function)
graph.add_node("LokiToolNode",loki_tool_function)
graph.add_node("K8sToolNode",k8s_tool_function)
graph.add_node("GitToolNode",git_tool_function)
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
graph.add_edge(START,"SupervisorNode")
graph.add_edge("PrometheusToolNode","SupervisorNode")
graph.add_edge("LokiToolNode","SupervisorNode")
graph.add_edge("K8sToolNode","SupervisorNode")
graph.add_edge("GitToolNode","SupervisorNode")
graph.add_edge("SummaryEvalNode", END)

agent_graph = graph.compile()

with open("../graph_diagram.png","wb") as fd:
    fd.write(agent_graph.get_graph().draw_mermaid_png())
