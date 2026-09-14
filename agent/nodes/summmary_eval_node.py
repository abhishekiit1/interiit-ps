from core.state import InvestigationState
from langchain_core.messages import SystemMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from yaml import safe_load

def summary_eval_function(state: InvestigationState) -> InvestigationState:
    """Your task is to evaluate the given hypotheses against the given evidence and confidence
    score. After evaluating, generate the Root Cause Analysis report."""
    try:
        summary_prompt = [SystemMessage(load_prompt("../prompts/Summary_Evaluation.yaml"))]
        response = llm.invoke([
            summary_prompt.format(
                incident_description=state["incident_description"],
                evidence=state["evidence"],
                hypotheses=state["hypotheses"],
                confidence=state["confidence"],
            )
        ])
        yaml_response = safe_load(response.content)
        state["final_rca"] = yaml_response["final_rca"]
        state["confidence"] = float(yaml_response["confidence"])
        state["confidence_level"] = yaml_response["confidence_level"]
        return state
    except Exception as error:
        raise RuntimeError(f'RCA Report generation failure:\nReason: {error}\n')