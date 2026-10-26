from unittest.mock import AsyncMock

import litellm
import pytest
from fastapi.testclient import TestClient
from litellm.types.utils import Choices, Message, ModelResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.creativity_agent import creativity_judge_agent
from app.agents.move_generator_agent import move_generator_agent
from app.api.deps import get_db
from app.core.errors import ToolUnavailableError
from app.main import app
from app.models.orm import Base


def _fake_response(content: str) -> ModelResponse:
    return ModelResponse(
        id="chatcmpl-test",
        choices=[
            Choices(
                index=0,
                message=Message(role="assistant", content=content),
                finish_reason="stop",
            )
        ],
        model="gpt-5-mini",
    )


def _word_response(word: str) -> ModelResponse:
    return _fake_response(f'{{"word": "{word}"}}')


def _creativity_response(creative: bool, reason: str) -> ModelResponse:
    return _fake_response(
        f'{{"creative": {"true" if creative else "false"}, "reason": "{reason}"}}'
    )


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _start_game(
    client, monkeypatch, username="jacky", difficulty="medium", opening_word="dragon"
):
    monkeypatch.setattr(
        move_generator_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_word_response(opening_word)),
    )
    response = client.post(
        "/game/start", json={"username": username, "difficulty": difficulty}
    )
    assert response.status_code == 200
    return response.json()["game_id"]


def test_malformed_creativity_json_falls_back_gracefully(client, monkeypatch):
    monkeypatch.setattr(
        "app.agents.validator_agent.dictionary_client.word_exists", lambda word: True
    )
    game_id = _start_game(client, monkeypatch)

    monkeypatch.setattr(
        creativity_judge_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(
            side_effect=[_fake_response("not json"), _fake_response("still not json")]
        ),
    )
    monkeypatch.setattr(
        move_generator_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_word_response("rabbit")),
    )

    response = client.post(f"/game/{game_id}/turn", json={"word": "nectar"})

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["score_breakdown"]["creative"] == 0


def test_malformed_move_generator_json_falls_back_to_wordlist(client, monkeypatch):
    monkeypatch.setattr(
        "app.agents.validator_agent.dictionary_client.word_exists", lambda word: True
    )
    game_id = _start_game(client, monkeypatch)

    monkeypatch.setattr(
        creativity_judge_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_creativity_response(True, "clever")),
    )
    monkeypatch.setattr(
        move_generator_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_fake_response("not json")),
    )

    response = client.post(f"/game/{game_id}/turn", json={"word": "nectar"})

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["ai_move"] is not None


def test_creativity_rate_limit_then_success(client, monkeypatch):
    monkeypatch.setattr(
        "app.agents.validator_agent.dictionary_client.word_exists", lambda word: True
    )
    game_id = _start_game(client, monkeypatch)

    rate_limit_error = litellm.RateLimitError(
        message="rate limited", model="gpt-5-mini", llm_provider="openai"
    )
    monkeypatch.setattr(
        creativity_judge_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(side_effect=[rate_limit_error, _creativity_response(True, "clever")]),
    )
    monkeypatch.setattr(
        move_generator_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_word_response("rabbit")),
    )

    response = client.post(f"/game/{game_id}/turn", json={"word": "nectar"})

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["score_breakdown"]["creative"] == 5


def test_creativity_persistent_rate_limit_falls_back(client, monkeypatch):
    monkeypatch.setattr(
        "app.agents.validator_agent.dictionary_client.word_exists", lambda word: True
    )
    game_id = _start_game(client, monkeypatch)

    rate_limit_error = litellm.RateLimitError(
        message="rate limited", model="gpt-5-mini", llm_provider="openai"
    )
    monkeypatch.setattr(
        creativity_judge_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(side_effect=rate_limit_error),
    )
    monkeypatch.setattr(
        move_generator_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_word_response("rabbit")),
    )

    response = client.post(f"/game/{game_id}/turn", json={"word": "nectar"})

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["score_breakdown"]["creative"] == 0


def test_move_generator_persistent_5xx_falls_back_to_wordlist(client, monkeypatch):
    monkeypatch.setattr(
        "app.agents.validator_agent.dictionary_client.word_exists", lambda word: True
    )
    game_id = _start_game(client, monkeypatch)

    server_error = litellm.InternalServerError(
        message="down", model="gpt-5-mini", llm_provider="openai"
    )
    monkeypatch.setattr(
        creativity_judge_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_creativity_response(True, "clever")),
    )
    monkeypatch.setattr(
        move_generator_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(side_effect=server_error),
    )

    response = client.post(f"/game/{game_id}/turn", json={"word": "nectar"})

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["ai_move"] is not None


def test_dictionary_outage_degrades_gracefully(client, monkeypatch):
    game_id = _start_game(client, monkeypatch)

    def _raise(word):
        raise ToolUnavailableError("dictionary down")

    monkeypatch.setattr(
        "app.agents.validator_agent.dictionary_client.word_exists", _raise
    )
    monkeypatch.setattr(
        creativity_judge_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_creativity_response(True, "clever")),
    )
    monkeypatch.setattr(
        move_generator_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_word_response("rabbit")),
    )

    response = client.post(f"/game/{game_id}/turn", json={"word": "nectar"})

    assert response.status_code == 200
    assert response.json()["accepted"] is True


def test_move_generator_total_exhaustion_returns_503_not_500(client, monkeypatch):
    monkeypatch.setattr(
        "app.agents.validator_agent.dictionary_client.word_exists", lambda word: True
    )
    game_id = _start_game(client, monkeypatch)

    monkeypatch.setattr(
        creativity_judge_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_creativity_response(True, "clever")),
    )
    monkeypatch.setattr(
        move_generator_agent._agent.model.llm_client,
        "acompletion",
        AsyncMock(return_value=_word_response("zzzznotaword")),
    )
    monkeypatch.setattr(
        "app.agents.move_generator_agent.load_wordlist", lambda difficulty: []
    )

    response = client.post(f"/game/{game_id}/turn", json={"word": "nectar"})

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "tool_unavailable"


@pytest.mark.parametrize(
    "word,expected_reason",
    [
        ("", "empty_input"),
        ("   ", "empty_input"),
        ("🔥日本語", "wrong_letter"),
        ("a" * 200, "invalid_format"),
    ],
)
def test_adversarial_inputs_rejected_without_crashing(
    client, monkeypatch, word, expected_reason
):
    game_id = _start_game(client, monkeypatch)

    response = client.post(f"/game/{game_id}/turn", json={"word": word})

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["reason"] == expected_reason
