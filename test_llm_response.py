import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), "agent"))
sys.path.append(os.path.join(os.getcwd(), "agent", "core"))
load_dotenv()

from agent.core.llm_init import llm
from langchain_core.messages import HumanMessage

def test():
    response = llm.invoke([HumanMessage(content="Hello, output exactly this YAML:\nhypotheses:\n- H1\nnext_step: 1")])
    print("Content Type:", type(response.content))
    print("Content:", response.content)

if __name__ == "__main__":
    test()
