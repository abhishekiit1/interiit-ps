from agent.core.tools import query_loki_logs

# The LogQL query to fetch the last 5 logs from the crashing cartservice
test_query = '{app="cartservice"}'

print(f"🤖 LLM decides to run LogQL: {test_query}\n")

# Execute the tool
result = query_loki_logs.invoke({"logql_query": test_query, "limit": 5})

print("📥 What the LLM actually 'reads' as the result:")
print("=" * 50)
print(result)
print("=" * 50)