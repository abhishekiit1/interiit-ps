# test_prom.py
from agent.core.tools import query_prometheus

# This is the exact PromQL query the Observability Specialist agent might generate
# to check how many times containers have restarted.
test_query = "kube_pod_container_status_restarts_total"

print(f"🤖 LLM decides to run: {test_query}\n")

# LangChain tools use the .invoke() method to execute
result = query_prometheus.invoke({"promql_query": test_query})

print("📥 What the LLM actually 'reads' as the result:")
print("=" * 100)
print(result)
print("=" * 100)