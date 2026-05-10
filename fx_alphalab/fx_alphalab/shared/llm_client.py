"""
Shared LLM client — used by all analysts and the orchestrator.
Thin wrapper around the OpenAI-compatible hosted Llama endpoint.
"""
import os
from openai import OpenAI

MODEL = "hosted_vllm/Llama-3.1-70B-Instruct"

_client = None


def get_llm_client() -> OpenAI:
    """Returns a singleton OpenAI client pointed at the hosted provider."""
    global _client
    if _client is None:
        base_url = os.getenv("OLLAMA_BASE_URL", "https://tokenfactory.esprit.tn/api")
        api_key = os.getenv("OLLAMA_API_KEY", "")
        if not api_key:
            raise ValueError("OLLAMA_API_KEY environment variable is not set")
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client