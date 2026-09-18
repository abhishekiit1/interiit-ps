from core.state import InvestigationState
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from yaml import safe_load

# the routing above it decides which tool to use it simply serves as proxy node for tools
# because adding one conditional edge to another was not possible
def tool_proxy(state: InvestigationState) -> InvestigationState:
    return state