import os
import logging
from openai import OpenAI


logger = logging.getLogger(__name__)


class LLMService:

    def __init__(self):

        self.providers = [

            # ==================================================
            # GROQ
            # ==================================================

            {
                "name": "Groq",

                "base_url": os.getenv(
                    "GROQ_BASE_URL",
                    "https://api.groq.com/openai/v1"
                ),

                "model": os.getenv(
                    "GROQ_MODEL_NAME",
                    "openai/gpt-oss-120b"
                ),

                "keys": [
                    os.getenv("GROQ_API_KEY_1"),
                    os.getenv("GROQ_API_KEY_2"),
                    os.getenv("GROQ_API_KEY_3"),
                ],
            },

            # ==================================================
            # CEREBRAS
            # ==================================================

            {
                "name": "Cerebras",

                "base_url": os.getenv(
                    "CEREBRAS_BASE_URL",
                    "https://api.cerebras.ai/v1"
                ),

                "model": os.getenv(
                    "CEREBRAS_MODEL_NAME",
                    "llama-3.3-70b"
                ),

                "keys": [
                    os.getenv("CEREBRAS_API_KEY_1"),
                    os.getenv("CEREBRAS_API_KEY_2"),
                    os.getenv("CEREBRAS_API_KEY_3"),
                    os.getenv("CEREBRAS_API_KEY_4"),
                ],
            },
        ]

        # ======================================================
        # REMOVE EMPTY KEYS
        # ======================================================

        for provider in self.providers:

            provider["keys"] = [
                key
                for key in provider["keys"]
                if key
            ]

        # ======================================================
        # REMOVE PROVIDERS WITHOUT KEYS
        # ======================================================

        self.providers = [
            provider
            for provider in self.providers
            if provider["keys"]
        ]

        if not self.providers:
            raise Exception(
                "No LLM API keys configured."
            )

        # ======================================================
        # ROTATION STATE
        # ======================================================

        self.provider_index = -1

        self.key_indexes = {
            provider["name"]: -1
            for provider in self.providers
        }

    # ==========================================================
    # ADMIN / RUNTIME STATUS
    # ==========================================================

    def get_runtime_status(self):

        providers = []

        for provider in self.providers:

            key_count = len(
                provider.get("keys", [])
            )

            providers.append({

                "name": provider.get("name"),

                "model": provider.get("model"),

                "base_url": provider.get("base_url"),

                "key_count": key_count,

                "configured": key_count > 0,

                "status": (
                    "Available"
                    if key_count > 0
                    else "Unavailable"
                )

            })

        provider_count = len(providers)

        return {

            "operational": provider_count > 0,

            "provider_count": provider_count,

            "providers": providers,

            "rotation_enabled": provider_count > 1,

            "primary_provider": (
                providers[0]["name"]
                if providers
                else "None"
            ),

            "secondary_provider": (
                providers[1]["name"]
                if len(providers) > 1
                else "None"
            ),

            "api_key_source": "Environment",

            "coach_enabled": provider_count > 0,

            "provider_abstraction": True

        }

    # ==========================================================
    # NEXT CLIENT
    # ==========================================================

    def _next_client(self):

        self.provider_index = (

            self.provider_index + 1

        ) % len(self.providers)

        provider = self.providers[
            self.provider_index
        ]

        provider_name = provider["name"]

        self.key_indexes[provider_name] = (

            self.key_indexes[provider_name] + 1

        ) % len(provider["keys"])

        key_index = self.key_indexes[
            provider_name
        ]

        api_key = provider["keys"][
            key_index
        ]

        client = OpenAI(

            api_key=api_key,

            base_url=provider["base_url"]

        )

        return (

            client,

            provider["model"],

            provider["name"]

        )

    # ==========================================================
    # CHAT
    # ==========================================================

    def chat(
        self,
        user_message,
        system_prompt,
        history=None
    ):

        if history is None:
            history = []

        messages = [

            {
                "role": "system",
                "content": system_prompt
            }

        ]

        messages.extend(history)

        messages.append({

            "role": "user",
            "content": user_message

        })

        # ======================================================
        # TOTAL AVAILABLE API KEYS
        # ======================================================

        total_attempts = sum(

            len(provider["keys"])

            for provider in self.providers

        )

        last_error = None

        # ======================================================
        # FAILOVER
        # ======================================================

        for attempt in range(total_attempts):

            client, model, provider = (
                self._next_client()
            )

            try:

                logger.info(
                    "FOCOST AI request: provider=%s model=%s attempt=%s",
                    provider,
                    model,
                    attempt + 1
                )

                response = (
                    client.chat.completions.create(

                        model=model,

                        messages=messages,

                        temperature=0.5,

                        max_tokens=800

                    )
                )

                content = (
                    response
                    .choices[0]
                    .message
                    .content
                )

                return {

                    "success": True,

                    "provider": provider,

                    "model": model,

                    "message": content

                }

            except Exception as e:

                last_error = e

                logger.warning(

                    "FOCOST AI provider failure: "
                    "provider=%s model=%s attempt=%s error=%s",

                    provider,
                    model,
                    attempt + 1,

                    type(e).__name__

                )

                continue

        # ======================================================
        # ALL PROVIDERS FAILED
        # ======================================================

        logger.error(

            "FOCOST AI unavailable after %s attempts. "
            "Last error type=%s",

            total_attempts,

            type(last_error).__name__
            if last_error
            else "Unknown"

        )

        return {

            "success": False,

            "message": (

                "FOCOST AI is temporarily unavailable. "

                "Please try again shortly."

            ),

            "error_code": "LLM_UNAVAILABLE",

        }