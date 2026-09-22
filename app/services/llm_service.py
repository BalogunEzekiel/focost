import os
import logging
import time

from openai import OpenAI
from openai import (
    APIStatusError,
    APIConnectionError,
    APITimeoutError,
)

logger = logging.getLogger(__name__)


class LLMService:
    """
    Centralized LLM provider service.

    Provider strategy:
    1. Use configured Groq keys only.
    2. Rotate through configured Groq API keys.
    3. Retry transient failures.
    4. Skip permanent failures.
    5. Protect providers from oversized requests.
    """

    # Conservative character guard.
    #
    # This is NOT intended to replace targeted DB retrieval.
    # It is a final safety mechanism against accidental oversized prompts.
    MAX_INPUT_CHARACTERS = 30000

    def __init__(self):
        self.providers = self._build_providers()

    # --------------------------------------------------------------
    # PROVIDERS
    # --------------------------------------------------------------

    def _get_keys(self, prefix):
        keys = []

        for index in range(1, 21):
            value = os.getenv(
                f"{prefix}_API_KEY_{index}"
            )

            if value:
                value = value.strip()

            if value:
                keys.append(value)

        return keys

    def _build_providers(self):
        providers = []

        groq_keys = self._get_keys("GROQ")

        if groq_keys:
            providers.append(
                {
                    "name": "Groq",
                    "base_url": os.getenv(
                        "GROQ_BASE_URL",
                        "https://api.groq.com/openai/v1",
                    ),
                    "model": os.getenv(
                        "GROQ_MODEL_NAME",
                        "openai/gpt-oss-120b",
                    ),
                    "keys": groq_keys,
                }
            )

        return providers

    # --------------------------------------------------------------
    # RUNTIME STATUS
    # --------------------------------------------------------------

    def get_runtime_status(self):
        providers = []

        for provider in self.providers:
            key_count = len(
                provider.get("keys", [])
            )

            providers.append(
                {
                    "name": provider.get("name"),
                    "model": provider.get("model"),
                    "base_url": provider.get(
                        "base_url"
                    ),
                    "key_count": key_count,
                    "configured": key_count > 0,
                    "status": (
                        "Available"
                        if key_count > 0
                        else "Unavailable"
                    ),
                }
            )

        provider_count = len(
            providers
        )

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
            "provider_abstraction": True,
        }

    # --------------------------------------------------------------
    # ERRORS
    # --------------------------------------------------------------

    def _status_code(self, error):
        return getattr(
            error,
            "status_code",
            None,
        )

    def _error_message(self, error):
        message = str(error).strip()

        if not message:
            return type(error).__name__

        return message[:1000]

    def _is_transient(self, error):
        status = self._status_code(error)

        if isinstance(
            error,
            (
                APIConnectionError,
                APITimeoutError,
            ),
        ):
            return True

        if status in {
            429,
            500,
            502,
            503,
            504,
        }:
            return True

        return False

    def _is_permanent(self, error):
        status = self._status_code(error)

        return status in {
            400,
            401,
            403,
            404,
            413,
            422,
        }

    # --------------------------------------------------------------
    # REQUEST SIZE
    # --------------------------------------------------------------

    def _estimate_input_characters(
        self,
        messages,
    ):
        total = 0

        for message in messages:
            content = message.get(
                "content",
                "",
            )

            if isinstance(
                content,
                str,
            ):
                total += len(content)

        return total

    def _validate_request_size(
        self,
        messages,
    ):
        characters = (
            self._estimate_input_characters(
                messages
            )
        )

        if (
            characters
            > self.MAX_INPUT_CHARACTERS
        ):
            logger.error(
                "FOCOST AI request rejected locally: "
                "input_characters=%s max=%s",
                characters,
                self.MAX_INPUT_CHARACTERS,
            )

            return False, characters

        return True, characters

    # --------------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------------

    def _request(
        self,
        provider,
        api_key,
        messages,
    ):
        valid, characters = (
            self._validate_request_size(
                messages
            )
        )

        if not valid:
            raise ValueError(
                "FOCOST AI request is too large. "
                f"Input contains approximately "
                f"{characters} characters."
            )

        client = OpenAI(
            api_key=api_key,
            base_url=provider["base_url"],
        )

        temperature = float(
            os.getenv(
                "FOCOST_AI_TEMPERATURE",
                "0.2",
            )
        )

        max_tokens = int(
            os.getenv(
                "FOCOST_AI_MAX_TOKENS",
                "250",
            )
        )

        kwargs = {
            "model": provider["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if (
            provider["name"] == "Groq"
            and provider["model"]
            in {
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
            }
        ):
            kwargs["reasoning_effort"] = os.getenv(
                "FOCOST_AI_REASONING_EFFORT",
                "low",
            )

        return client.chat.completions.create(
            **kwargs
        )

    # --------------------------------------------------------------
    # CHAT
    # --------------------------------------------------------------

    def chat(
        self,
        user_message,
        system_prompt,
        history=None,
    ):
        if history is None:
            history = []

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        if not self.providers:
            return {
                "success": False,
                "message": (
                    "FOCOST AI is not configured. "
                    "Please contact the administrator."
                ),
                "error_code": "LLM_NOT_CONFIGURED",
            }

        provider_errors = []

        for provider in self.providers:
            provider_name = provider["name"]
            model = provider["model"]
            keys = provider["keys"]

            logger.info(
                "FOCOST AI provider starting: "
                "provider=%s model=%s keys=%s",
                provider_name,
                model,
                len(keys),
            )

            for key_index, api_key in enumerate(
                keys,
                start=1,
            ):
                max_attempts = 2

                for retry in range(
                    max_attempts
                ):
                    logger.info(
                        "FOCOST AI request: "
                        "provider=%s model=%s "
                        "key=%s/%s retry=%s",
                        provider_name,
                        model,
                        key_index,
                        len(keys),
                        retry + 1,
                    )

                    try:
                        response = self._request(
                            provider=provider,
                            api_key=api_key,
                            messages=messages,
                        )

                        content = ""

                        if response.choices:
                            content = (
                                response
                                .choices[0]
                                .message
                                .content
                                or ""
                            ).strip()

                        usage = getattr(
                            response,
                            "usage",
                            None,
                        )

                        input_tokens = int(
                            getattr(
                                usage,
                                "prompt_tokens",
                                0,
                            )
                            or 0
                        )

                        output_tokens = int(
                            getattr(
                                usage,
                                "completion_tokens",
                                0,
                            )
                            or 0
                        )

                        total_tokens = int(
                            getattr(
                                usage,
                                "total_tokens",
                                0,
                            )
                            or 0
                        )

                        logger.info(
                            "FOCOST AI success: "
                            "provider=%s model=%s "
                            "key=%s/%s "
                            "input_tokens=%s "
                            "output_tokens=%s "
                            "total_tokens=%s",
                            provider_name,
                            model,
                            key_index,
                            len(keys),
                            input_tokens,
                            output_tokens,
                            total_tokens,
                        )

                        return {
                            "success": True,
                            "provider": provider_name,
                            "model": model,
                            "message": content,
                            "usage": {
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": total_tokens,
                            },
                        }

                    except Exception as error:
                        status = self._status_code(
                            error
                        )

                        error_message = (
                            self._error_message(
                                error
                            )
                        )

                        provider_errors.append(
                            {
                                "provider": provider_name,
                                "model": model,
                                "key_index": key_index,
                                "status_code": status,
                                "error_type": type(
                                    error
                                ).__name__,
                                "message": error_message,
                            }
                        )

                        logger.warning(
                            "FOCOST AI provider failure: "
                            "provider=%s model=%s "
                            "key=%s/%s retry=%s "
                            "status=%s error_type=%s "
                            "error=%s",
                            provider_name,
                            model,
                            key_index,
                            len(keys),
                            retry + 1,
                            status,
                            type(error).__name__,
                            error_message,
                            exc_info=True,
                        )

                        if self._is_permanent(
                            error
                        ):
                            break

                        if self._is_transient(
                            error
                        ):
                            if (
                                retry
                                < max_attempts - 1
                            ):
                                time.sleep(1.0)
                                continue

                        break

        logger.error(
            "FOCOST AI unavailable after "
            "all providers/keys. "
            "provider_errors=%s",
            provider_errors,
        )

        return {
            "success": False,
            "message": (
                "FOCOST AI is temporarily unavailable. "
                "Please try again shortly."
            ),
            "error_code": "LLM_UNAVAILABLE",
            "provider_errors": provider_errors,
        }