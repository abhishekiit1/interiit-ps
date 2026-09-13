from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt.tool_node import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import load_prompt
from state import InvestigationState
from tools import(
    query_loki_logs,
    query_prometheus,
    get_pod_status,
    get_recent_git_changes
)
import yaml
available_tools = [
    query_prometheus,
    query_loki_logs,
    get_pod_status,
    get_recent_git_changes
]

# intializing chatmodel/llm
llm = ChatGoogleGenerativeAI(model="gemini-3.7-flash")
llm = llm.bind_tools(available_tools)


# initial investigation function -- called at the very beginning
def initial_investigation(state: InvestigationState) -> InvestigationState:
    try:
        initial_prompt = load_prompt("../prompts/Investigation_Begin.yaml")
        initial_response = llm.invoke(initial_prompt.format(alert= state["incident_description"]))
        yaml_response = yaml.safe_load(initial_response.content)
        state["next_node"] = yaml_response["next_step"]
        return state
    except Exception as error:
        raise RuntimeError(
            f'Initial RCA investigation failed:\nReason: {error}.'
        )
# iterative investigation function -- making conclusions from given logs/evidence
def iterative_investigation(state: InvestigationState) -> InvestigationState:
    try:
        return state
    except Exception as error:
        raise RuntimeError(
            f'Iterative Investigation failure:\nReason: {error}.\n'
        )
# supervisor node function
def supervisor_function(state: InvestigationState) -> InvestigationState:
    steps = len(state["investigation_steps"])
    next_step = state["next_node"]
    if steps == 0:
        #initial investigation
        return initialInvestigation(state)
    elif next_step != "0000":
        return state
    else:
        return iterative_investigation(state)




def tool_routing(state: InvestigationState) -> str:
    next_node = state["next_node"]

    if next_node == "0000":
        return 
    

# initializing graph
graph = StateGraph()

prometheus_tool = ToolNode(tools = query_prometheus)
loki_tool = ToolNode(tools = query_loki_logs)
k8s_tool = ToolNode(tools = get_pod_status)
git_tool = ToolNode(tools = get_recent_git_changes)
# initializing nodes
graph.add_node("SupervisorNode",supervisor_function)
graph.add_node("LokiToolNode",loki_tool)
graph.add_node("K8sToolNode",k8s_tool)
graph.add_node("GitToolNode",git_tool)

graph.add_conditional_edges(
    "SupervisorNode",
    supervisor_routing,
    {
        "summary":"ConfidenceReviewNode",
        "tool":tool_routing
    }
)
graph.add_conditional_edges(
    supervisor_routing,
    tool_routing,
    {
        "1":"PrometheusToolNode",
        "2":"LokiToolNode",
        "4":"K8sToolNode",
        "8":"GitToolNode"
    }
)
graph.add_edge(START,"SupervisorNode")
graph.add_edge("PrometheusToolNode","SupervisorNode")
graph.add_edge("LokiToolNode","SupervisorNode")
graph.add_edge("K8sNode","SupervisorNode")
graph.add_edge("GitToolNode","SupervisorNode")

agent_graph = graph.compile()


