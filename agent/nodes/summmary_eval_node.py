from core.state import InvestigationState
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from yaml import safe_loads

def summary_eval_function(state: InvestigationState) -> InvestigationState:
    """Your task is to evaluate the given hypotheses against the given evidence and confidence
    score. After evaluating, generate the Root Cause Analysis report"""
    try:
        return state
    except Exception as error:
        raise RuntimeError(f'RCA Report generation failure:\nReason: {error}')