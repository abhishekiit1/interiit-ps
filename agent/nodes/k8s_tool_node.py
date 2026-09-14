import time
from langchain_core.messages import SystemMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from core.state import InvestigationState
from core.tools import get_pod_status
from yaml import safe_load

def k8s_tool_function(state: InvestigationState) -> InvestigationState:
    """
    Kubernetes Expert Node.
    Analyzes the incident and decides whether to fetch all pod statuses or drill down into a specific suspect app.
    """
    try:
        prompt_template = load_prompt("../prompts/Kubernetes_Query.yaml")
        formatted_prompt = prompt_template.format(
            incident_description=state.get("incident_description", ""),
            suspect_components=state.get("suspect_components", []),
            hypotheses=state.get("hypotheses", []),
            evidence=state.get("evidence", [])
        )
        
        response = llm.invoke([SystemMessage(content=formatted_prompt)])
        yaml_response = safe_load(response.content.replace('```yaml', '').replace('```', ''))
        app_label = yaml_response.get("app_label", "").strip()
        last_error = None

        for attempt in range(1, 4):
            try:
                # Invoke the tool with the app_label parameter
                result = get_pod_status.invoke({"namespace": "default", "app_label": app_label})

                if result.startswith("Kubernetes query failed:"):
                    raise RuntimeError(result)

                # Append the tool's raw result directly to the evidence list
                state["evidence"] = [*state.get("evidence", []), result]
                return state
            except Exception as error:
                last_error = error
        
        raise RuntimeError(f"Kubernetes query failed after 3 attempts: {last_error}")
    except Exception as error:
        raise RuntimeError(f"Kubernetes Tool Error:\nReason: {error}") from error