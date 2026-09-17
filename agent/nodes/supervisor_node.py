import os
from core.state import InvestigationState
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from yaml import safe_load

# initial investigation function -- called at the very beginning
def initial_investigation(state: InvestigationState) -> InvestigationState:
    """
    For very first iterative investigation step, since we do not have any initial hypothese,
    we need to generate one by observing the alert message only. Once the hypotheses is generated,
    we need to call a suitable tool or tools as per our requirement. 
    """
    try:
        prompt_template = load_prompt(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../prompts/Investigation_Begin.yaml"))
        # In a real system, incident_timestamp would be parsed from the alert. 
        # For our swarm, we'll initialize it here if it's empty.
        import datetime
        if not state.get("incident_timestamp"):
            state["incident_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
        formatted_prompt = prompt_template.format(alert=state.get("incident_description", ""))
        initial_response = llm.invoke([HumanMessage(content=formatted_prompt)])
        
        raw_content = initial_response.content.replace('```yaml', '').replace('```', '')
        try:
            yaml_response = safe_load(raw_content)
        except Exception:
            import re
            yaml_response = {}
            ns_match = re.search(r'next_step:.*?(\d+)', raw_content, re.DOTALL)
            yaml_response["next_step"] = int(ns_match.group(1)) if ns_match else 0
            yaml_response["hypotheses"] = []
            
        state["hypotheses"] = yaml_response.get("hypotheses", [])
        
        # Handle next_step being returned as a list (e.g., [1] instead of 1)
        ns = yaml_response.get("next_step", 0)
        if isinstance(ns, list):
            ns = ns[0] if len(ns) > 0 else 0
        state["next_node"] = int(ns)
        
        state["suspect_components"] = [] # Initialize empty for the first step
        return state
    except Exception as error:
        raise RuntimeError(
            f'Initial RCA investigation failed:\nReason: {error}.'
        )
# iterative investigation function -- making conclusions from given logs/evidence
def iterative_investigation(state: InvestigationState) -> InvestigationState:
    """
    When we have our initail hypotheses, we need to verify it with the evidence we have collected so 
    far with the various tools we have called. Once the hypotheses are updated, we must think about the 
    next tool call (may not call next tool if confidence is high), along with the confidence score for 
    the solution.
    """
    # Safeguard against infinite loops
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    if state["iteration_count"] >= 4:
        state["next_node"] = 0
        state["evidence"] = [*state.get("evidence", []), "SYSTEM_NOTE: Max iterations reached (4). Forcing summary generation."]
        return state

    try:
        prompt_template = load_prompt(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../prompts/Iterative_Investigation.yaml"))
        formatted_prompt = prompt_template.format(
            incident_description=state.get("incident_description", ""),
            incident_timestamp=state.get("incident_timestamp", ""),
            suspect_components=state.get("suspect_components", []),
            hypotheses=state.get("hypotheses", []),
            evidence=state.get("evidence", [])
        )
        initial_response = llm.invoke([HumanMessage(content=formatted_prompt)])
        
        raw_content = initial_response.content.replace('```yaml', '').replace('```', '')
        try:
            yaml_response = safe_load(raw_content)
        except Exception:
            import re
            yaml_response = {}
            ns_match = re.search(r'next_step:.*?(\d+)', raw_content, re.DOTALL)
            yaml_response["next_step"] = int(ns_match.group(1)) if ns_match else 0
            conf_match = re.search(r'confidence:.*?([\d.]+)', raw_content, re.DOTALL)
            yaml_response["confidence"] = float(conf_match.group(1)) if conf_match else 0.0
            yaml_response["suspect_components"] = state.get("suspect_components", [])
            yaml_response["hypotheses"] = []

        state["suspect_components"] = yaml_response.get("suspect_components", state.get("suspect_components", []))
        state["hypotheses"] = yaml_response.get("hypotheses", [])
        
        ns = yaml_response.get("next_step", 0)
        if isinstance(ns, list):
            ns = ns[0] if len(ns) > 0 else 0
        state["next_node"] = int(ns)
        
        conf = yaml_response.get("confidence", 0.0)
        if isinstance(conf, list):
            conf = conf[0] if len(conf) > 0 else 0.0
        state["confidence"] = float(conf)

        return state
    except Exception as error:
        raise RuntimeError(
            f'Iterative Investigation failure:\nReason: {error}.\n'
        )
# supervisor node function
def supervisor_function(state: InvestigationState) -> InvestigationState:
    """
    You are a supervisor RCA agent, which will be trigerred by alert manager and you will receive
    the alert. You have to use the tools and identify which tools to call, make/update hypotheses.
    Based on the evidence you have collected.
    Args:
        alert: generated by alert manager of prometheus 
    """
    if not state.get("hypotheses"):
        # initial investigation
        return initial_investigation(state)
    else:
        # tools are called need to reiterate on the evidence collected
        return iterative_investigation(state)

