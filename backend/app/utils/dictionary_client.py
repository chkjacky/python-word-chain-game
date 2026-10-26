import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.core.errors import ToolUnavailableError

DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"


class _RetryableDictionaryError(Exception):
    pass


class DictionaryClient:
    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout

    def word_exists(self, word: str) -> bool:
        try:
            response = self._fetch(word)
        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            _RetryableDictionaryError,
        ) as exc:
            raise ToolUnavailableError(
                f"dictionary API unavailable for '{word}'"
            ) from exc

        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        raise ToolUnavailableError(
            f"dictionary API returned unexpected status {response.status_code}"
        )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(0),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.ConnectError, _RetryableDictionaryError)
        ),
        reraise=True,
    )
    def _fetch(self, word: str) -> httpx.Response:
        response = httpx.get(DICTIONARY_API_URL.format(word=word), timeout=self.timeout)
        if response.status_code >= 500:
            raise _RetryableDictionaryError(f"status {response.status_code}")
        return response


dictionary_client = DictionaryClient()
