"""Shared LLM client factory for the hosted Ollama provider."""
import os
from openai import OpenAI

MODEL = "hosted_vllm/Llama-3.1-70B-Instruct"

_client = None

def get_llm_client() -> OpenAI:
    """Returns a singleton OpenAI client pointed at the hosted Ollama provider."""
    global _client
    if _client is None:
        base_url = os.getenv("OLLAMA_BASE_URL", "https://tokenfactory.esprit.tn/api")
        api_key = os.getenv("OLLAMA_API_KEY")
        if not api_key:
            raise ValueError("OLLAMA_API_KEY environment variable is not set")
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


if __name__ == "__main__":
    print("Testing LLM client...")
    client = get_llm_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Say 'LLM client works!'"}],
        max_tokens=50,
    )
    print(f"OK: {response.choices[0].message.content.strip()}")