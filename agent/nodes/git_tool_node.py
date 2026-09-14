import time
from langchain_core.messages import SystemMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from core.state import InvestigationState
from core.tools import get_recent_git_changes
from yaml import safe_load

def git_tool_function(state: InvestigationState) -> InvestigationState:
    """
    Git History Expert Node.
    Analyzes the incident and decides whether to fetch recent git commits.
    """
    try:
        prompt_template = load_prompt("../prompts/Git_status.yaml")
        formatted_prompt = prompt_template.format(
            incident_description=state.get("incident_description", ""),
            suspect_components=state.get("suspect_components", []),
            hypotheses=state.get("hypotheses", []),
            evidence=state.get("evidence", [])
        )
        
        response = llm.invoke([SystemMessage(content=formatted_prompt)])
        yaml_response = safe_load(response.content.replace('```yaml', '').replace('```', ''))
        run_git_tool = yaml_response.get("run_git_tool", False)
        
        if run_git_tool:
            # Invoke the tool
            result = get_recent_git_changes.invoke({"repo_path": "."})
            
            # Append the tool's raw result directly to the evidence list
            state["evidence"] = [*state.get("evidence", []), result]
        else:
            state["evidence"] = [*state.get("evidence", []), "<untrusted_data> Git Tool: LLM decided git commits were irrelevant to the current hypotheses. </untrusted_data>"]
            
        return state
    except Exception as error:
        raise RuntimeError(f"Git Tool Error:\nReason: {error}") from error