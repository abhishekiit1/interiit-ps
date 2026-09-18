from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openrouter import ChatOpenRouter
import sys
import os
import time
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Primary: Gemini (free, high quota)
_gemini_llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", max_retries=0)

# Fallback 1: OpenRouter primary key
_openrouter_llm_1 = ChatOpenRouter(
    model="google/gemini-3.5-flash",
    openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
    max_tokens=512,
    max_retries=0,
)

# Fallback 2: OpenRouter alternate key
_openrouter_llm_2 = ChatOpenRouter(
    model="google/gemini-3.5-flash",
    openrouter_api_key=os.getenv("OPENROUTER_API_KEY_ALT"),
    max_tokens=512,
    max_retries=0,
)

class RateLimitedLLM:
    def __init__(self, providers):
        self._providers = providers  # list of (name, llm) tuples
        self._last_call_time = 0  # Track time between calls
        
    def _normalize_content(self, resp):
        """Normalize content to string if SDK returns list of blocks."""
        if isinstance(resp.content, list):
            text_content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in resp.content
            )
            resp.content = text_content
        return resp
        
    def invoke(self, *args, **kwargs):
        last_error = None
        for i, (name, provider_llm) in enumerate(self._providers):
            # For the primary provider (Gemini), try max 2 times. For fallbacks, 1 time.
            max_attempts = 2 if i == 0 else 1
            for attempt in range(max_attempts):
                try:
                    # Rate limit: ensure minimum 4 seconds between any two LLM calls
                    elapsed = time.time() - self._last_call_time
                    wait_time = max(0, 4.0 - elapsed)
                    if wait_time > 0:
                        time.sleep(wait_time)
                    
                    self._last_call_time = time.time()
                    resp = provider_llm.invoke(*args, **kwargs)
                    resp = self._normalize_content(resp)
                    print(f"  ✅ LLM call succeeded via {name} (attempt {attempt + 1})")
                    return resp
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    is_transient = any(kw in error_msg for kw in [
                        "503", "unavailable", "429", "resourceexhausted", 
                        "quota", "rate limit", "high demand", "overloaded",
                        "key limit exceeded", "more credits", "fewer max_tokens",
                        "resource_exhausted", "too many requests", "payment"
                    ])
                    if is_transient:
                        if attempt < max_attempts - 1:
                            # Short exponential backoff
                            backoff = 5 * (2 ** attempt)  # 5s
                            print(f"  ⚠️ {name} rate limited (attempt {attempt + 1}/{max_attempts}), retrying in {backoff}s...")
                            time.sleep(backoff)
                            continue
                        elif i < len(self._providers) - 1:
                            next_name = self._providers[i + 1][0]
                            print(f"  ⚠️ {name} exhausted after {max_attempts} attempts, falling back to {next_name}...")
                            break  # Move to next provider
                        else:
                            raise e
                    else:
                        # Non-transient error: raise immediately
                        raise e
        
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
                    
    def __getattr__(self, name):
        return getattr(self._providers[0][1], name)

llm = RateLimitedLLM([
    ("Gemini-Direct", _gemini_llm),
    ("OpenRouter-Key1", _openrouter_llm_1),
    ("OpenRouter-Key2", _openrouter_llm_2),
])
