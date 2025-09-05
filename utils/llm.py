# utils/llm.py
"""
Gemini LLM client factory.

Environment variables:
  - GOOGLE_API_KEY : required
  - GEMINI_MODEL   : optional (default: 'gemini-1.5-flash')

Returns:
  - Callable[[str], str]  OR None (if no key available)

Usage:
    from utils.llm import get_llm_client
    llm = get_llm_client()
    if llm:
        print(llm("Summarize this text."))
"""

import os
from typing import Callable, Optional

def get_llm_client() -> Optional[Callable[[str], str]]:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None  # No key → fallback to heuristics

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    try:
        import google.generativeai as genai
    except Exception as e:
        raise RuntimeError(
            "⚠️ Missing google-generativeai package. Install with: pip install google-generativeai"
        ) from e

    # Configure Gemini
    genai.configure(api_key=api_key)
    model_client = genai.GenerativeModel(model)

    def _call(prompt: str, *, temperature: float = 0.2, max_tokens: int = 512) -> str:
        """
        Call Gemini and return plain text output.
        """
        try:
            response = model_client.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
        except Exception as exc:
            raise RuntimeError(f"Gemini API request failed: {exc}")

        # Extract text safely
        try:
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            if hasattr(response, "candidates") and response.candidates:
                cand = response.candidates[0]
                if hasattr(cand, "content") and getattr(cand.content, "parts", None):
                    return "".join(p.text for p in cand.content.parts if getattr(p, "text", None)).strip()
            return str(response)
        except Exception:
            return str(response)

    return _call
