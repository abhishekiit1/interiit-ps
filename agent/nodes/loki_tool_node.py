import time
from langchain_core.messages import SystemMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from core.state import InvestigationState
from core.tools import query_loki_logs
from yaml import safe_load

def loki_tool_function(state: InvestigationState) -> InvestigationState:
    """
    Loki LogQL Expert Node.
    Analyzes the incident and decides what LogQL query to execute to fetch relevant application logs.
    """
    try:
        prompt_template = load_prompt("../prompts/Loki_Query.yaml")
        formatted_prompt = prompt_template.format(
            incident_description=state.get("incident_description", ""),
            incident_timestamp=state.get("incident_timestamp", ""),
            suspect_components=state.get("suspect_components", []),
            hypotheses=state.get("hypotheses", []),
            evidence=state.get("evidence", [])
        )
        
        response = llm.invoke([SystemMessage(content=formatted_prompt)])
        yaml_response = safe_load(response.content.replace('```yaml', '').replace('```', ''))
        logql_query = yaml_response.get("logql_query", "").strip()
        last_error = None

        for attempt in range(1, 4):
            try:
                # Invoke the tool with the logql_query parameter
                result = query_loki_logs.invoke({"logql_query": logql_query})

                if result.startswith("Loki query failed:"):
                    raise RuntimeError(result)

                # Append the tool's raw result directly to the evidence list
                state["evidence"] = [*state.get("evidence", []), result]
                return state
            except Exception as error:
                last_error = error
        
        raise RuntimeError(f"Loki query failed after 3 attempts: {last_error}")
    except Exception as error:
        raise RuntimeError(f"Loki Tool Error:\nReason: {error}") from error