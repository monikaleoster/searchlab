from openai import OpenAI, APIStatusError, APITimeoutError


class LlmTimeoutError(Exception):
    pass


class LlmApiError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class LlmClient:
    def __init__(self, model: str, api_key: str | None = None):
        if not api_key:
            raise LlmApiError(0, "OPENAI_API_KEY environment variable is not set.")
        self._model = model
        self._client = OpenAI(api_key=api_key, timeout=30.0)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0,
            )
            return resp.choices[0].message.content or ""
        except APITimeoutError as e:
            raise LlmTimeoutError("LLM call timed out after 30 seconds.") from e
        except APIStatusError as e:
            raise LlmApiError(e.status_code, e.message) from e
