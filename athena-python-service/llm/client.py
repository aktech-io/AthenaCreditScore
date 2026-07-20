from __future__ import annotations

import json
import os
import structlog

import openai

logger = structlog.get_logger(__name__)


class LLMClient:
    """Dual-mode LLM client: OpenAI API or any OpenAI-compatible local endpoint (Ollama/vLLM)."""

    def __init__(self):
        # Default is LOCAL (DPA 2019 posture): credit-profile prompts contain
        # personal data and must not leave the environment unless explicitly
        # opted into a hosted provider via LLM_PROVIDER=openai.
        provider = os.getenv("LLM_PROVIDER", "local")
        default_model = "gpt-4o-mini" if provider == "openai" else "qwen2.5-coder:7b"
        self.model = os.getenv("LLM_MODEL", default_model)

        if provider == "openai":
            # A missing key must not crash service startup: the SDK raises on
            # api_key=None. Calls will fail cleanly and return the 0-adjustment
            # fallback in get_score_adjustment.
            self.client = openai.AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY") or "unset",
            )
        else:
            # Ollama / vLLM expose an OpenAI-compatible /v1 endpoint
            base_url = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")
            self.client = openai.AsyncOpenAI(
                api_key="ollama",  # dummy – local servers don't validate this
                base_url=base_url,
            )

        logger.info("LLM client initialised", provider=provider, model=self.model)

    async def get_score_adjustment(self, prompt: str) -> dict:
        """
        Calls the LLM with the scoring prompt.
        Returns a dict with keys: adjustment (int -50..+50), reasoning (list[str]).
        """
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=600,
            )
            raw = resp.choices[0].message.content
            data = json.loads(raw)

            # Clamp adjustment to safe range
            adjustment = int(data.get("adjustment", 0))
            adjustment = max(-50, min(50, adjustment))
            reasoning = data.get("reasoning", [])

            return {"adjustment": adjustment, "reasoning": reasoning, "raw": raw}

        except Exception as exc:
            logger.error("LLM call failed", error=str(exc))
            # Safe fallback — no adjustment, neutral reasoning
            return {
                "adjustment": 0,
                "reasoning": ["LLM analysis unavailable."],
                "raw": "",
            }
