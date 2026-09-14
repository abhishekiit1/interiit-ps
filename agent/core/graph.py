from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage
from langgraph.prebuilt.tool_node import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import load_prompt
from state import InvestigationState
import yaml

# importing tools
from tools import(
    query_loki_logs,
    query_prometheus,
    get_pod_status,
    get_recent_git_changes
)
available_tools = [
    query_prometheus,
    query_loki_logs,
    get_pod_status,
    get_recent_git_changes
]
# importing nodes
from nodes.supervisor_node import (supervisor_function, initial_investigation, iterative_investigation)
from nodes.summmary_eval_node import (summary_eval_function)

from nodes.tool_proxy_node import(tool_proxy)

def supervisor_routing(state: InvestigationState) -> str:
    next_step = state["next_step"]
    if next_step == 0:
        return "summary"
    else:
        return "tool"


def tool_routing(state: InvestigationState) -> str:
    next_node = state["next_node"]

    if next_node == "0000":
        return 

def summary_eval(state: InvestigationState) -> InvestigationState:
    try:

        return state
    except Exception as error:
        raise RuntimeError(f'Summary and evaluation failed:\n Reason: {error}')    

# initializing graph
graph = StateGraph(InvestigationState)

prometheus_tool = ToolNode(tools = query_prometheus)
loki_tool = ToolNode(tools = query_loki_logs)
k8s_tool = ToolNode(tools = get_pod_status)
git_tool = ToolNode(tools = get_recent_git_changes)
# initializing nodes
graph.add_node("SupervisorNode",supervisor_function)
graph.add_node("PrometheusToolNode",prometheus_tool)
graph.add_node("LokiToolNode",loki_tool)
graph.add_node("K8sToolNode",k8s_tool)
graph.add_node("GitToolNode",git_tool)
graph.add_node("ToolProxyNode",tool_proxy)
graph.add_conditional_edges(
    "SupervisorNode",
    supervisor_routing,
    {
        "summary":"SummaryEvalNode",
        "tool":"ToolProxyNode"
    }
)
graph.add_conditional_edges(
    supervisor_routing,
    tool_routing,
    {
        1:"PrometheusToolNode",
        2:"LokiToolNode",
        4:"K8sToolNode",
        8:"GitToolNode"
    }
)
graph.add_conditional_edges(
    "SummaryEvalNode",
    loop_checker,
    {
        "loop":"SupervisorNode"
        "summary":END
    }
)
graph.add_edge(START,"SupervisorNode")
graph.add_edge("PrometheusToolNode","SupervisorNode")
graph.add_edge("LokiToolNode","SupervisorNode")
graph.add_edge("K8sNode","SupervisorNode")
graph.add_edge("GitToolNode","SupervisorNode")

agent_graph = graph.compile()

with open("../graph_diagram.png","wb") as fd:
    fd.write(agent_graph.get_graph().draw_mermaid_png())
