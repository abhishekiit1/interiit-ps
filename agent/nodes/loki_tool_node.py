import os
import time
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from core.state import InvestigationState
from yaml import safe_load
import requests
from langchain_core.tools import tool

# The Loki port-forward address
LOKI_URL = "http://localhost:3100/loki/api/v1/query_range"

@tool
def query_loki_logs(logql_query: str, limit: int = 50) -> str:
    """
    Executes a LogQL query against the Loki log aggregation server.
    Use this tool to fetch application logs, error messages, or stack traces 
    from specific containers to identify internal code failures or database timeouts.
    
    Args:
        logql_query: A valid LogQL string (e.g., '{app="checkoutservice"} |= "error"').
        limit: Maximum number of log lines to return (default 50 to prevent context overflow).
    """
    try:
        response = requests.get(LOKI_URL, params={'query': logql_query, 'limit': limit}, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('data', {}).get('result', [])
        if not results:
            return "No logs found for this query."
            
        formatted_output = ""
        for res in results:
            # Loki returns values as a list of [timestamp, log_line]
            values = res.get('values', [])
            for val in values:
                log_line = val[1].strip()
                # Truncate extremely long single log lines to avoid context blowup
                if len(log_line) > 500:
                    log_line = log_line[:500] + "... (truncated)"
                formatted_output += f"{log_line}\n"
                
        # Mandatory sandboxing: Treat all application logs as untrusted input
        return f"<untrusted_data>\n{formatted_output.strip()}\n</untrusted_data>"
        
    except Exception as e:
        return f"Loki query failed: {str(e)}"

def loki_tool_function(state: InvestigationState) -> InvestigationState:
    """
    Loki LogQL Expert Node.
    Analyzes the incident and decides what LogQL query to execute to fetch relevant application logs.
    """
    try:
        prompt_template = load_prompt(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../prompts/Loki_Query.yaml"))
        formatted_prompt = prompt_template.format(
            incident_description=state.get("incident_description", ""),
            incident_timestamp=state.get("incident_timestamp", ""),
            suspect_components=state.get("suspect_components", []),
            hypotheses=state.get("hypotheses", []),
            evidence=state.get("evidence", [])
        )
        
        response = llm.invoke([HumanMessage(content=formatted_prompt)])
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