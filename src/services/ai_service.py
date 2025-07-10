import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODEL = "mistralai/mistral-7b-instruct:free"

class LLMServiceError(Exception):
    pass

def call_llm(prompt, model=DEFAULT_MODEL, system_prompt=None, max_tokens=512):
    if not OPENROUTER_API_KEY:
        raise LLMServiceError("OPENROUTER_API_KEY not set in environment.")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens
    }
    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
        # Log rate limit headers
        print("OpenRouter Rate Limit:", response.headers.get("X-RateLimit-Limit"))
        print("OpenRouter Remaining:", response.headers.get("X-RateLimit-Remaining"))
        reset_ts = response.headers.get("X-RateLimit-Reset")
        if reset_ts:
            try:
                import datetime
                reset_dt = datetime.datetime.fromtimestamp(int(reset_ts) / 1000)
                print("OpenRouter Reset (human):", reset_dt.strftime("%Y-%m-%d %H:%M:%S"))
            except Exception as e:
                print("Could not parse reset timestamp:", e)
        if response.status_code == 429:
            # Quota or rate limit exceeded
            raise LLMServiceError("quota_exceeded")
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except LLMServiceError as e:
        raise
    except Exception as e:
        raise LLMServiceError(f"LLM call failed: {e}")

# Usage example (remove or comment out in production):
# if __name__ == "__main__":
#     print(call_llm("Explique la recette d'une pizza margherita."))

# Note: Requires 'python-dotenv' and 'requests' packages. 