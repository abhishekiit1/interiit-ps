from langchain_core.messages import SystemMessage, HumanMessage
from agent.core.llm_init import llm

try:
    print("Testing SystemMessage only...")
    res = llm.invoke([SystemMessage(content="Hello world")])
    print(res)
except Exception as e:
    print(f"Error: {e}")

try:
    print("\nTesting HumanMessage only...")
    res = llm.invoke([HumanMessage(content="Hello world")])
    print(res)
except Exception as e:
    print(f"Error: {e}")
