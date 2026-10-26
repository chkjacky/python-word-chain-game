import httpx
import pytest

from app.core.errors import ToolUnavailableError
from app.utils.dictionary_client import DictionaryClient


def test_word_exists_returns_true_on_200(httpx_mock):
    httpx_mock.add_response(status_code=200, json=[{"word": "nectar"}])

    client = DictionaryClient()
    assert client.word_exists("nectar") is True


def test_word_exists_returns_false_on_404_without_retry(httpx_mock):
    httpx_mock.add_response(status_code=404)

    client = DictionaryClient()
    assert client.word_exists("zzzznotaword") is False
    assert len(httpx_mock.get_requests()) == 1


def test_word_exists_raises_tool_unavailable_after_exhausting_retries_on_500(
    httpx_mock,
):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)

    client = DictionaryClient()
    with pytest.raises(ToolUnavailableError):
        client.word_exists("nectar")


def test_word_exists_raises_tool_unavailable_on_timeout(httpx_mock):
    httpx_mock.add_exception(httpx.TimeoutException("timed out"))
    httpx_mock.add_exception(httpx.TimeoutException("timed out"))

    client = DictionaryClient()
    with pytest.raises(ToolUnavailableError):
        client.word_exists("nectar")
