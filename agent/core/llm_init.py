from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openrouter import ChatOpenRouter
import sys
import os
import time
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_base_llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", max_retries=10)

class RateLimitedLLM:
    def __init__(self, llm):
        self._llm = llm
        
    def invoke(self, *args, **kwargs):
        max_attempts = 5
        base_delay = 4
        
        for attempt in range(max_attempts):
            try:
                # Add a static delay to respect the 15 RPM limit (1 req / 4 secs)
                time.sleep(4)
                resp = self._llm.invoke(*args, **kwargs)
                # Normalize content to string if Langchain returns a list of blocks
                if isinstance(resp.content, list):
                    text_content = "".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in resp.content
                    )
                    resp.content = text_content
                return resp
            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "resourceexhausted" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                    if attempt == max_attempts - 1:
                        raise e
                    print(f"Rate limit hit. Retrying in {base_delay} seconds...")
                    time.sleep(base_delay)
                    base_delay *= 2  # Exponential backoff
                else:
                    raise e
                    
    def __getattr__(self, name):
        return getattr(self._llm, name)

llm = RateLimitedLLM(_base_llm)
