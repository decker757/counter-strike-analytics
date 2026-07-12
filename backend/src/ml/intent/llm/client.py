"""Ollama LLM client wrapper.

Handles communication with a local Ollama instance for natural language
coaching insights. All methods handle the case where Ollama is not running
by returning structured error/status responses rather than crashing.
"""

import json
import time
from typing import Optional


class LLMClient:
    """Wrapper around Ollama's REST API for local LLM inference.

    Uses Ollama's /api/generate endpoint for text generation.
    Falls back gracefully when Ollama is not running.

    Requires: ollama (pip install ollama)
    """

    # Default model — small, fast, good quality
    DEFAULT_MODEL = "llama3.2:3b"

    def __init__(self, model: str = "", host: str = "http://localhost:11434"):
        """Initialize LLM client.

        Args:
            model: Ollama model name (default: llama3.2:3b)
            host: Ollama API host
        """
        self.model = model or self.DEFAULT_MODEL
        self.host = host
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if Ollama server is running and model is available.

        Returns:
            True if Ollama is reachable
        """
        if self._available is not None:
            return self._available

        try:
            import urllib.request
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
                # Check if our model (or a close match) is available
                model_base = self.model.split(":")[0]
                self._available = any(
                    m.startswith(model_base) or m == self.model
                    for m in models
                )
                if not self._available:
                    print(f"Model {self.model} not found in Ollama. Available: {models}")
        except Exception as e:
            print(f"Ollama not available: {e}")
            self._available = False

        return self._available

    def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> dict:
        """Generate text from the LLM.

        Args:
            prompt: User prompt / question
            system: System prompt (role definition)
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (0-1)

        Returns:
            {"text": "...", "status": "ok"} on success,
            {"text": "", "status": "unavailable", "message": "..."} if Ollama not running
        """
        if not self.is_available():
            return {
                "text": "",
                "status": "unavailable",
                "message": (
                    f"Ollama is not running or model '{self.model}' is not installed. "
                    f"Install with: ollama pull {self.model}"
                ),
            }

        try:
            import urllib.request

            body = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
            )

            t0 = time.time()
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                elapsed = time.time() - t0
                return {
                    "text": result.get("response", ""),
                    "status": "ok",
                    "elapsed_seconds": round(elapsed, 2),
                    "model": self.model,
                }

        except Exception as e:
            return {
                "text": "",
                "status": "error",
                "message": f"LLM generation failed: {e}",
            }

    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> dict:
        """Multi-turn chat with conversation history.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            max_tokens: Maximum response tokens
            temperature: Sampling temperature

        Returns:
            {"text": "...", "status": "ok"} or error dict
        """
        if not self.is_available():
            return {
                "text": "",
                "status": "unavailable",
                "message": f"Ollama not running. Install: ollama pull {self.model}",
            }

        try:
            import urllib.request

            body = json.dumps({
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.host}/api/chat",
                data=body,
                headers={"Content-Type": "application/json"},
            )

            t0 = time.time()
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                return {
                    "text": result.get("message", {}).get("content", ""),
                    "status": "ok",
                    "elapsed_seconds": round(time.time() - t0, 2),
                    "model": self.model,
                }

        except Exception as e:
            return {
                "text": "",
                "status": "error",
                "message": f"Chat generation failed: {e}",
            }
