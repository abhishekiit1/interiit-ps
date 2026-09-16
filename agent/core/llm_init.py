from langchain_google_genai import ChatGoogleGenerativeAI
import sys
import os
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# intializing chatmodel/llm
llm = ChatGoogleGenerativeAI(model="gemini-3.7-flash")
