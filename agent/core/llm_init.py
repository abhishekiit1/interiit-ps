from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import bind_tools
from tools import ( 
    get_pod_status,
    get_recent_git_changes,
    query_loki_logs,
    query_prometheus
)

available_tools = [ query_prometheus,
                    get_pod_status,
                    get_recent_git_changes,
                    query_loki_logs
                ]

# intializing chatmodel/llm
llm = ChatGoogleGenerativeAI(model="gemini-3.7-flash")
llm = llm.bind_tools(available_tools)
