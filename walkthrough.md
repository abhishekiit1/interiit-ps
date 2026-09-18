# RCA Agent Fix Walkthrough

The RCA generation agent is now fully functional and resilient! I've resolved all the blockers you highlighted. Here's a summary of the fixes implemented to ensure it successfully generates RCA reports.

## 1. LLM Resilience & Rate Limit Mitigation
The primary reason the agent was failing was aggressive rate-limiting on the Gemini API and exhaustion of OpenRouter credits, combined with fragile error handling. 
- **Multi-Provider Fallback**: Implemented a robust `RateLimitedLLM` wrapper in [`llm_init.py`](file:///Users/abhishekchaubey/Desktop/prepathon/14sept/interiit-ps/agent/core/llm_init.py). It now attempts Gemini up to 3 times, and gracefully falls back through your OpenRouter keys if exhausted.
- **Exponential Backoff**: Implemented proper exponential backoff (`10s`, `20s`) for `429` Rate Limit and `503` Overloaded errors.
- **Credit Limits**: Reduced `max_tokens` for OpenRouter back to `1024` to prevent `PaymentRequiredResponseError` due to low token credits on the keys.

## 2. Multi-Tool Graph Routing
The LangGraph architecture was previously dropping tools because it only processed the first bit of the `next_node` bitmask.
- **Bitmask Clearing**: Updated the `tool_routing` logic in [`graph.py`](file:///Users/abhishekchaubey/Desktop/prepathon/14sept/interiit-ps/agent/core/graph.py) to sequentially pop the lowest-order bit (e.g., `bit_to_run = next_node & -next_node`) and clear it (`next_node &= ~bit_to_run`).
- **Sequential Execution**: The graph now correctly loops through the `ToolProxyNode`, running one tool at a time until `next_node == 0`, at which point it returns to the Supervisor.

## 3. Prompt Engineering Fixes
- The `next_step` outputs were previously requested as YAML list items (`- an integer`), causing the LLM to return arrays like `[6]` instead of scalars `6`, breaking bitwise operations.
- Updated [`Investigation_Begin.yaml`](file:///Users/abhishekchaubey/Desktop/prepathon/14sept/interiit-ps/agent/prompts/Investigation_Begin.yaml) and [`Iterative_Investigation.yaml`](file:///Users/abhishekchaubey/Desktop/prepathon/14sept/interiit-ps/agent/prompts/Iterative_Investigation.yaml) to explicitly demand scalar outputs (`next_step: 5`).

## 4. Robust YAML Parsing
LLMs occasionally wrap YAML in markdown fences or omit standard formatting, causing `PyYAML` to parse the output as a scalar string rather than a dictionary.
- Implemented robust `safe_load` fallback blocks across all Tool Nodes ([`prometheus_tool_node.py`](file:///Users/abhishekchaubey/Desktop/prepathon/14sept/interiit-ps/agent/nodes/prometheus_tool_node.py), [`loki_tool_node.py`](file:///Users/abhishekchaubey/Desktop/prepathon/14sept/interiit-ps/agent/nodes/loki_tool_node.py), etc.) that explicitly validate `isinstance(yaml_response, dict)`.
- If parsing fails, it safely falls back to Regex extraction to find the necessary query parameters.

## 5. Visibility and Logging
- Added comprehensive `print()` logging across the Supervisor, Summary Eval, and Tool nodes to make it perfectly clear what the agent is doing, which tools it is calling, and what evidence it retrieves.

> [!TIP]
> **API Limits**: The current setup uses a lot of prompt tokens due to the heavy K8s and Prometheus logs. If you continue hitting rate limits on the free Gemini tier, consider setting `max_retries=5` for Gemini in `llm_init.py` or adding credits to your OpenRouter keys.

The E2E test proved that the agent can now successfully sequence through multiple tools (like Loki + K8s), gather evidence (e.g., identifying OOMKilled containers), and produce a final RCA!
