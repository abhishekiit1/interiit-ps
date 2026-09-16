import time
from langchain_core.messages import SystemMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from core.state import InvestigationState
from yaml import safe_load
import os
import subprocess
from langchain_core.tools import tool

@tool
def get_recent_git_changes(repo_path: str = ".") -> str:
    """
    Fetches the recent commit history and configuration changes from the local Git repository.
    Use this tool to investigate if a recent deployment, image change, or YAML configuration 
    update caused the current incident.
    
    Args:
        repo_path: The directory path to the git repository (defaults to current directory ".").
    """
    try:
        # Verify it is a valid git repository first
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return "Error: No Git repository found in the specified path."

        # Execute 'git log' to get the last 3 commits and the files they modified
        result = subprocess.run(
            ["git", "log", "-n", "3", "--stat", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        git_output = result.stdout.strip()
        if not git_output:
            return "No recent commits found."

        # Wrap in sandboxing tags to prevent prompt injection from commit messages
        return f"<untrusted_data>\n{git_output}\n</untrusted_data>"
        
    except subprocess.CalledProcessError as e:
        return f"Git command failed: {e.stderr}"
    except Exception as e:
        return f"An error occurred while fetching git changes: {str(e)}"

def git_tool_function(state: InvestigationState) -> InvestigationState:
    """
    Git History Expert Node.
    Analyzes the incident and decides whether to fetch recent git commits.
    """
    try:
        prompt_template = load_prompt(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../prompts/Git_status.yaml"))
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