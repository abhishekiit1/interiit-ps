from core.state import InvestigationState
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from yaml import safe_loads


def tool_proxy(state: InvestigationState) -> InvestigationState:
    return state