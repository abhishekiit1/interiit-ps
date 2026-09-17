from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openrouter import ChatOpenRouter
import sys
import os
import time
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Primary: Gemini (free, high quota)
_gemini_llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", max_retries=2)

# Fallback 1: OpenRouter primary key
_openrouter_llm_1 = ChatOpenRouter(
    model="google/gemini-3.5-flash",
    openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
    max_retries=0,
)

# Fallback 2: OpenRouter alternate key
_openrouter_llm_2 = ChatOpenRouter(
    model="google/gemini-3.5-flash",
    openrouter_api_key=os.getenv("OPENROUTER_API_KEY_ALT"),
    max_retries=0,
)

class RateLimitedLLM:
    def __init__(self, providers):
        self._providers = providers  # list of (name, llm) tuples
        
    def invoke(self, *args, **kwargs):
        last_error = None
        for i, (name, provider_llm) in enumerate(self._providers):
            try:
                time.sleep(4)  # Rate limit: ~15 RPM
                resp = provider_llm.invoke(*args, **kwargs)
                # Normalize content to string if SDK returns list of blocks
                if isinstance(resp.content, list):
                    text_content = "".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in resp.content
                    )
                    resp.content = text_content
                return resp
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                is_transient = any(kw in error_msg for kw in [
                    "503", "unavailable", "429", "resourceexhausted", 
                    "quota", "rate limit", "high demand", "overloaded",
                    "key limit exceeded"
                ])
                if is_transient and i < len(self._providers) - 1:
                    next_name = self._providers[i + 1][0]
                    print(f"⚠️ {name} unavailable, falling back to {next_name}...")
                    continue
                else:
                    raise e
        
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
                    
    def __getattr__(self, name):
        return getattr(self._providers[0][1], name)

llm = RateLimitedLLM([
    ("Gemini-Direct", _gemini_llm),
    ("OpenRouter-Key1", _openrouter_llm_1),
    ("OpenRouter-Key2", _openrouter_llm_2),
])
